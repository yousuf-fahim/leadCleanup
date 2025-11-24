import streamlit as st
import pandas as pd
import usaddress
import io
import zipfile
from openpyxl import Workbook
import string
import time
import re
import logging
from datetime import datetime
import os
import gc  # For garbage collection
try:
    import psutil  # For memory monitoring
except ImportError:
    pass  # Will handle in code

# Set up logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Column mapping between old and new formats
OLD_TO_NEW_COLUMN_MAPPING = {
    # Core identity columns
    'FIRST_NAME': 'FIRST_NAME',
    'LAST_NAME': 'LAST_NAME',
    
    # Address columns
    'PERSONAL_ADDRESS': 'PERSONAL_ADDRESS',
    'PERSONAL_CITY': 'PERSONAL_CITY',
    'PERSONAL_STATE': 'PERSONAL_STATE',
    'PERSONAL_ZIP': 'PERSONAL_ZIP',
    'PERSONAL_ZIP4': 'PERSONAL_ZIP4',
    
    # Phone columns
    'DIRECT_NUMBER': 'DIRECT_NUMBER',
    'MOBILE_PHONE': 'MOBILE_PHONE',
    'PERSONAL_PHONE': 'PERSONAL_PHONE',
    'DNC': 'DNC',
    
    # Demographics
    'AGE_RANGE': 'AGE_RANGE',
    'CHILDREN': 'CHILDREN',
    'GENDER': 'GENDER',
    'HOMEOWNER': 'HOMEOWNER',
    'MARRIED': 'MARRIED',
    'NET_WORTH': 'NET_WORTH',
    'INCOME_RANGE': 'INCOME_RANGE',
    
    # Email columns
    'BUSINESS_EMAIL': 'BUSINESS_EMAIL',
    'PERSONAL_EMAIL': 'PERSONAL_EMAILS',  # Note: old had singular, new has plural
    'ADDITIONAL_PERSONAL_EMAILS': 'PERSONAL_EMAILS',  # Map to same field
    'SHA256_PERSONAL_EMAIL': 'SHA256_PERSONAL_EMAIL',
    'SHA256_BUSINESS_EMAIL': 'SHA256_BUSINESS_EMAIL',
    
    # Professional columns
    'JOB_TITLE': 'JOB_TITLE',
    'DEPARTMENT': 'DEPARTMENT',
    'SENIORITY_LEVEL': 'SENIORITY_LEVEL',
    'LINKEDIN_URL': 'LINKEDIN_URL',
    
    # Company columns
    'COMPANY_NAME': 'COMPANY_NAME',
    'COMPANY_ADDRESS': 'COMPANY_ADDRESS',
    'COMPANY_DOMAIN': 'COMPANY_DOMAIN',
    'COMPANY_EMPLOYEE_COUNT': 'COMPANY_EMPLOYEE_COUNT',
    'COMPANY_LINKEDIN_URL': 'COMPANY_LINKEDIN_URL',
    'COMPANY_PHONE': 'COMPANY_PHONE',
    'COMPANY_REVENUE': 'COMPANY_REVENUE',
    'COMPANY_SIC': 'COMPANY_SIC',
    'COMPANY_NAICS': 'COMPANY_NAICS',
    'COMPANY_CITY': 'COMPANY_CITY',
    'COMPANY_STATE': 'COMPANY_STATE',
    'COMPANY_ZIP': 'COMPANY_ZIP',
    'COMPANY_INDUSTRY': 'COMPANY_INDUSTRY',
    
    # Professional address
    'PROFESSIONAL_ADDRESS': 'PROFESSIONAL_ADDRESS',
    'PROFESSIONAL_ADDRESS_2': 'PROFESSIONAL_ADDRESS_2',
    'PROFESSIONAL_CITY': 'PROFESSIONAL_CITY',
    'PROFESSIONAL_STATE': 'PROFESSIONAL_STATE',
    'PROFESSIONAL_ZIP': 'PROFESSIONAL_ZIP',
    'PROFESSIONAL_ZIP4': 'PROFESSIONAL_ZIP4',
    
    # Skiptrace columns
    'SKIPTRACE_CREDIT_RATING': 'SKIPTRACE_CREDIT_RATING',
    'SKIPTRACE_DNC': 'SKIPTRACE_DNC',
    'SKIPTRACE_EXACT_AGE': 'SKIPTRACE_EXACT_AGE',
    'SKIPTRACE_B2B_COMPANY_NAME': 'SKIPTRACE_B2B_COMPANY_NAME',
    'SKIPTRACE_B2B_PHONE': 'SKIPTRACE_B2B_PHONE',
    'SKIPTRACE_B2B_SOURCE': 'SKIPTRACE_B2B_SOURCE',
    'SKIPTRACE_B2B_WEBSITE': 'SKIPTRACE_B2B_WEBSITE'
}

# New format specific columns that don't exist in old format
NEW_FORMAT_SPECIFIC_COLUMNS = [
    'UUID', 'HEADLINE', 'INFERRED_YEARS_EXPERIENCE', 'COMPANY_NAME_HISTORY',
    'JOB_TITLE_HISTORY', 'EDUCATION_HISTORY', 'COMPANY_DESCRIPTION',
    'TWITTER_URL', 'FACEBOOK_URL', 'SOCIAL_CONNECTIONS', 'SKILLS', 'INTERESTS',
    'SKIPTRACE_MATCH_SCORE', 'SKIPTRACE_NAME', 'SKIPTRACE_ADDRESS',
    'SKIPTRACE_CITY', 'SKIPTRACE_STATE', 'SKIPTRACE_ZIP',
    'SKIPTRACE_LANDLINE_NUMBERS', 'SKIPTRACE_WIRELESS_NUMBERS',
    'SKIPTRACE_ETHNIC_CODE', 'SKIPTRACE_LANGUAGE_CODE', 'SKIPTRACE_IP',
    'SKIPTRACE_B2B_ADDRESS', 'DEEP_VERIFIED_EMAILS'
]

def detect_input_format(df):
    """
    Detect whether the input file is in old or new format
    Returns: 'old', 'new', or 'unknown'
    """
    # Check for new format specific columns
    new_format_indicators = ['UUID', 'HEADLINE', 'DEEP_VERIFIED_EMAILS', 'SKILLS']
    new_format_score = sum(1 for col in new_format_indicators if col in df.columns)
    
    # Check for old format specific patterns
    old_format_indicators = ['BUSINESS_EMAIL_VALIDATION_STATUS', 'PERSONAL_EMAIL_VALIDATION_STATUS', 
                           'SOCIAL_CONNECTIONS', 'LAST_UPDATED']
    old_format_score = sum(1 for col in old_format_indicators if col in df.columns)
    
    # Additional checks for column structure differences
    if 'PERSONAL_EMAIL' in df.columns and 'PERSONAL_EMAILS' not in df.columns:
        old_format_score += 1
    elif 'PERSONAL_EMAILS' in df.columns and 'PERSONAL_EMAIL' not in df.columns:
        new_format_score += 1
    
    # Decision logic
    if new_format_score > old_format_score:
        return 'new'
    elif old_format_score > new_format_score:
        return 'old'
    else:
        # If scores are equal, check for presence of UUID (strong new format indicator)
        if 'UUID' in df.columns:
            return 'new'
        else:
            return 'old'  # Default to old format for compatibility

def normalize_dataframe(df, detected_format):
    """
    Normalize DataFrame to a consistent internal format
    """
    if detected_format == 'old':
        return normalize_old_format(df)
    elif detected_format == 'new':
        return normalize_new_format(df)
    else:
        # Unknown format - try to work with it as-is
        return df.copy()

def normalize_old_format(df):
    """
    Normalize old format to internal standard
    """
    normalized_df = df.copy()
    
    # Handle email columns - old format has singular PERSONAL_EMAIL
    if 'PERSONAL_EMAIL' in normalized_df.columns and 'PERSONAL_EMAILS' not in normalized_df.columns:
        normalized_df['PERSONAL_EMAILS'] = normalized_df['PERSONAL_EMAIL']
    
    # Ensure DNC column is properly formatted
    if 'DNC' in normalized_df.columns:
        # Convert boolean or other formats to Y/N
        normalized_df['DNC'] = normalized_df['DNC'].apply(lambda x: 'Y' if str(x).upper() in ['Y', 'YES', 'TRUE', '1'] else 'N')
    
    return normalized_df

def normalize_new_format(df):
    """
    Normalize new format to internal standard
    """
    normalized_df = df.copy()
    
    # Handle email columns - new format may have different structure
    if 'PERSONAL_EMAILS' in normalized_df.columns and 'PERSONAL_EMAIL' not in normalized_df.columns:
        # Extract first email from PERSONAL_EMAILS for compatibility
        normalized_df['PERSONAL_EMAIL'] = normalized_df['PERSONAL_EMAILS'].apply(
            lambda x: str(x).split(',')[0].strip() if pd.notna(x) and str(x) != '' else ''
        )
    
    # Handle phone number columns that might have different formats
    phone_cols = ['MOBILE_PHONE', 'DIRECT_NUMBER', 'PERSONAL_PHONE']
    for col in phone_cols:
        if col in normalized_df.columns:
            # New format might have phone numbers in different format
            normalized_df[col] = normalized_df[col].apply(lambda x: str(x) if pd.notna(x) else '')
    
    # Handle DNC columns that might be formatted differently
    if 'DNC' not in normalized_df.columns:
        # Create DNC column if it doesn't exist
        normalized_df['DNC'] = 'N'
    else:
        # Ensure proper Y/N format
        normalized_df['DNC'] = normalized_df['DNC'].apply(lambda x: 'Y' if str(x).upper() in ['Y', 'YES', 'TRUE', '1'] else 'N')
    
    return normalized_df

def get_format_info(df, detected_format):
    """
    Get information about the detected format for user display
    """
    info = {
        'format': detected_format,
        'total_columns': len(df.columns),
        'total_rows': len(df)
    }
    
    if detected_format == 'old':
        info['description'] = "Classic address cleaner format"
        info['key_features'] = [
            "Standard address and contact fields",
            "Single personal email column",
            "Traditional column structure"
        ]
    elif detected_format == 'new':
        info['description'] = "Enhanced format with additional data"
        info['key_features'] = [
            "UUID for unique identification",
            "Enhanced social and professional data",
            "Deep verified emails",
            "Skills and interests data"
        ]
    else:
        info['description'] = "Unknown or custom format"
        info['key_features'] = [
            "Will attempt to process with available columns"
        ]
    
    return info

# Add CSS for responsive design - optimized
st.markdown("""
<style>
/* Base theme styles */
body {background-color: #FAFAFA; color: #212121;}
h1, h2, h3, h4, h5, h6 {color: #0D47A1;}

/* Dark mode overrides */
@media (prefers-color-scheme: dark) {
    body {background-color: #121212; color: #ECEFF1;}
    h1, h2, h3, h4, h5, h6 {color: #BBDEFB;}
    .stTextInput input, .stTextArea textarea, .st-download-button input, .stButton button {
        background-color: #202020; color: #BBDEFB;
    }
}

/* Mobile and tablet optimizations */
@media (max-width: 768px) {
    .stButton button {width: 100%; padding: 0.8rem 1rem; margin: 0.5rem 0; font-size: 1rem;}
    .stSelectbox, .stMultiselect {margin-bottom: 1.5rem;}
    .block-container {padding-top: 1rem; padding-bottom: 1rem;}
    p, li {font-size: 1rem; line-height: 1.5;}
    .stDownloadButton button {
        background-color: #4CAF50;
        color: white;
        padding: 0.8rem 0.5rem;
        width: 100%;
        margin: 0.7rem 0;
        border-radius: 0.3rem;
    }
    h1 {font-size: 1.8rem !important;}
    h2 {font-size: 1.5rem !important;}
    h3 {font-size: 1.2rem !important;}
    input, textarea {font-size: 16px !important;}
}

/* UI element enhancements */
.stProgress .st-bo {background-color: #4CAF50;}
.stFileUploader {border: 1px dashed #ccc; border-radius: 0.5rem; padding: 1rem; margin-bottom: 1rem;}
.stAlert {border-radius: 0.5rem;}
div[data-testid="stText"] div:has(span:contains("✅")), div.stSuccess {
    background-color: #E8F5E9;
    padding: 1rem;
    border-left: 4px solid #4CAF50;
    border-radius: 0.3rem;
    margin: 1rem 0;
}

/* Tab styling */
div[data-testid="stHorizontalBlock"] div[data-testid="column"] div[role="tab"] {
    background-color: #f0f2f6;
    border-radius: 0.5rem 0.5rem 0 0;
    padding: 1rem 1.5rem;
    margin-right: 0.25rem;
}

div[data-testid="stHorizontalBlock"] div[data-testid="column"] div[role="tab"][aria-selected="true"] {
    background-color: #0D47A1;
    color: white;
}

div[data-testid="stHorizontalBlock"] div[data-testid="column"] div[role="tabpanel"] {
    background-color: #f8f9fa;
    border-radius: 0 0.5rem 0.5rem 0.5rem;
    padding: 1rem;
    border: 1px solid #eaecef;
}

/* Help tooltips */
.tooltip {
    position: relative;
    display: inline-block;
    cursor: help;
}
.tooltip .tooltiptext {
    visibility: hidden;
    width: 200px;
    background-color: #555;
    color: #fff;
    text-align: center;
    border-radius: 6px;
    padding: 5px;
    position: absolute;
    z-index: 1;
    bottom: 125%;
    left: 50%;
    margin-left: -100px;
    opacity: 0;
    transition: opacity 0.3s;
}
.tooltip:hover .tooltiptext {
    visibility: visible;
    opacity: 1;
}

/* Format indicator styling */
.format-indicator {
    padding: 0.5rem 1rem;
    border-radius: 0.5rem;
    margin: 1rem 0;
    border-left: 4px solid;
}
.format-old {
    background-color: #E3F2FD;
    border-left-color: #2196F3;
    color: #1565C0;
}
.format-new {
    background-color: #E8F5E9;
    border-left-color: #4CAF50;
    color: #2E7D32;
}
.format-unknown {
    background-color: #FFF3E0;
    border-left-color: #FF9800;
    color: #F57C00;
}
</style>
""", unsafe_allow_html=True)

# Initialize session state for user preferences
if 'user_preferences' not in st.session_state:
    st.session_state['user_preferences'] = {
        'batch_size': 2000,
        'last_option': None,
        'dark_mode': False,
        'show_preview': True,
        'max_preview_rows': 5,
        'auto_clean_addresses': True,
        'default_output_format': 'csv'
    }

# Define abbreviation dictionaries with uppercase keys
directional_abbr = {
    'N': 'North', 'S': 'South', 'E': 'East', 'W': 'West',
    'NE': 'Northeast', 'NW': 'Northwest', 'SE': 'Southeast', 'SW': 'Southwest',
    'NORTH': 'North', 'SOUTH': 'South', 'EAST': 'East', 'WEST': 'West',
    'NORTHEAST': 'Northeast', 'NORTHWEST': 'Northwest', 'SOUTHEAST': 'Southeast', 'SOUTHWEST': 'Southwest'
}

street_type_abbr = {
    'ST': 'Street', 'AVE': 'Avenue', 'BLVD': 'Boulevard', 'RD': 'Road',
    'LN': 'Lane', 'DR': 'Drive', 'CT': 'Court', 'PL': 'Plaza',
    'SQ': 'Square', 'TER': 'Terrace', 'CIR': 'Circle', 'PKWY': 'Parkway',
    'TRL': 'Trail', 'TRCE': 'Trace', 'HWY': 'Highway', 'CTR': 'Center',
    'SPG': 'Spring', 'LK': 'Lake', 'ALY': 'Alley', 'BND': 'Bend', 'BRG': 'Bridge',
    'BYU': 'Bayou', 'CLF': 'Cliff', 'COR': 'Corner', 'CV': 'Cove', 'CRK': 'Creek',
    'XING': 'Crossing', 'GDN': 'Garden', 'GLN': 'Glen', 'GRN': 'Green',
    'HBR': 'Harbor', 'HOLW': 'Hollow', 'IS': 'Island', 'JCT': 'Junction',
    'KNL': 'Knoll', 'MDWS': 'Meadows', 'MTN': 'Mountain', 'PASS': 'Pass',
    'PT': 'Point', 'RNCH': 'Ranch', 'SHRS': 'Shores', 'STA': 'Station',
    'VLY': 'Valley', 'VW': 'View', 'WLK': 'Walk',
    'ANX': 'Annex', 'ARC': 'Arcade', 'AV': 'Avenue', 'BCH': 'Beach',
    'BG': 'Burg', 'BGS': 'Burgs', 'BLF': 'Bluff', 'BLFS': 'Bluffs',
    'BOT': 'Bottom', 'BR': 'Branch', 'BRK': 'Brook', 'BRKS': 'Brooks',
    'BTW': 'Between', 'CMN': 'Common', 'CMP': 'Camp', 'CNYN': 'Canyon',
    'CPE': 'Cape', 'CSWY': 'Causeway', 'CLB': 'Club', 'CON': 'Corner',
    'CORS': 'Corners', 'CP': 'Camp', 'CRES': 'Crescent', 'CRST': 'Crest',
    'XRD': 'Crossroad', 'EXT': 'Extension', 'FALLS': 'Falls', 'FRK': 'Fork',
    'FRKS': 'Forks', 'FT': 'Fort', 'FWY': 'Freeway', 'GDNS': 'Gardens',
    'GTWAY': 'Gateway', 'HGHTS': 'Heights', 'HVN': 'Haven', 'HD': 'Head',
    'HLLS': 'Hills', 'INLT': 'Inlet', 'JCTS': 'Junctions', 'KY': 'Key',
    'KYS': 'Keys', 'LNDG': 'Landing', 'LGT': 'Light', 'LGTS': 'Lights',
    'LF': 'Loaf', 'MNR': 'Manor', 'MLS': 'Mills', 'MSSN': 'Mission',
    'MT': 'Mount', 'NCK': 'Neck', 'ORCH': 'Orchard', 'OVAL': 'Oval',
    'PRK': 'Park', 'PKWYS': 'Parkways', 'PLN': 'Plain', 'PLZ': 'Plaza',
    'PRT': 'Port', 'PR': 'Prairie', 'RAD': 'Radial', 'RDG': 'Ridge',
    'RIV': 'River', 'RDGE': 'Ridge', 'RUN': 'Run', 'SHL': 'Shoal',
    'SHLS': 'Shoals', 'SKWY': 'Skyway', 'SPGS': 'Springs', 'SPUR': 'Spur',
    'STRM': 'Stream', 'STM': 'Stream', 'TRFY': 'Terrace', 'TRWY': 'Throughway',
    'TPKE': 'Turnpike', 'UN': 'Union', 'VLG': 'Village', 'VIS': 'Vista',
    'WAY': 'Way', 'EXPY': 'Expressway', 'FRWY': 'Freeway', 'TUNL': 'Tunnel',
    'PLNS': 'Plains'
}

unit_abbr = {
    'APT': 'Apartment', 'STE': 'Suite', 'BLDG': 'Building',
    'UNIT': 'Unit', 'RM': 'Room', 'FL': 'Floor', 'DEP': 'Department',
    'OFC': 'Office', 'SP': 'Space', 'LOT': 'Lot', 'TRLR': 'Trailer',
    'HANGAR': 'Hangar', 'SLIP': 'Slip', 'PIER': 'Pier', 'DOCK': 'Dock'
}


# Helper function to expand a single word
def expand_word(word):
    cleaned_word = word.rstrip(string.punctuation)
    upper_cleaned = cleaned_word.upper()
    return directional_abbr.get(upper_cleaned,
                                street_type_abbr.get(upper_cleaned,
                                                    unit_abbr.get(upper_cleaned, word)))


# Updated clean_address function
@st.cache_data
def clean_address(address):
    """Parse and expand abbreviations in an address with a robust fallback."""
    if pd.isna(address) or address == "":
        return ""
    
    try:
        parsed, address_type = usaddress.tag(address)
        if address_type == 'Street Address':
            cleaned_components = []
            for key, value in parsed.items():
                words = value.split()
                expanded_words = [expand_word(word) for word in words]
                expanded_value = " ".join(expanded_words)
                cleaned_components.append(expanded_value)
            return ' '.join(cleaned_components)
        elif address_type == 'PO Box':
            return 'PO Box ' + parsed['USPSBoxID']
        else:
            words = address.split()
            cleaned = [expand_word(word) for word in words]
            return ' '.join(cleaned)
    except usaddress.RepeatedLabelError:
        words = address.split()
        cleaned = [expand_word(word) for word in words]
        return ' '.join(cleaned)
    except Exception as e:
        logger.error(f"Error cleaning address '{address}': {str(e)}")
        return address  # Return original if any error occurs


# Validate phone number function
@st.cache_data
def validate_phone(phone):
    """Validate and format phone numbers"""
    if pd.isna(phone) or phone == "":
        return ""
    
    # Remove all non-digit characters
    digits = re.sub(r'\D', '', str(phone))
    
    # Check if we have a valid number of digits
    if len(digits) == 10:
        return f"({digits[:3]}) {digits[3:6]}-{digits[6:]}"

    elif len(digits) == 11 and digits[0] == '1':
        return f"({digits[1:4]}) {digits[4:7]}-{digits[7:]}"

    elif len(digits) > 0:  # Return any non-empty digits in a basic format
        return digits
    else:
        return ""  # Return empty string if no digits


# Function to split dataframe into batches
@st.cache_data
def split_dataframe(df, max_rows):
    return [df[i:i + max_rows] for i in range(0, len(df), max_rows)]


# Function to process and clean data
@st.cache_data(show_spinner=False)
def process_data(df, option, clean_addresses=True):
    """Process dataframe based on selected option with error handling"""
    try:
        start_time = time.time()
        
        # Make a copy to avoid modifying the original
        processed_df = df.copy()
        
        # Clean and process addresses if needed
        if clean_addresses:
            if option in ["Address + HoNWIncome", "Address + HoNWIncome & Phone", 
                        "Full Combined Address", "Phone & Credit Score", "Split by State",
                        "ZIP Split: Address+HoNW", "ZIP Split: Address+HoNW+Phone"]:
                # Filter for rows with addresses
                processed_df = processed_df[processed_df['PERSONAL_ADDRESS'].notna()]
                # Apply address cleaning with progress tracking
                processed_df['PERSONAL_ADDRESS_CLEAN'] = processed_df['PERSONAL_ADDRESS'].apply(clean_address)
            elif option == "Complete Contact Export":
                # For complete export, don't filter out rows without addresses
                if 'PERSONAL_ADDRESS' in processed_df.columns:
                    # Only clean addresses that exist
                    processed_df['PERSONAL_ADDRESS_CLEAN'] = processed_df['PERSONAL_ADDRESS'].apply(
                        lambda x: clean_address(x) if pd.notna(x) else x
                    )
        
        # Further processing based on option...
        # (The option-specific logic will be implemented in the main processing flow)
        
        processing_time = time.time() - start_time
        logger.info(f"Processed {len(processed_df)} rows in {processing_time:.2f} seconds")
        
        return processed_df
    except Exception as e:
        logger.error(f"Error in process_data: {str(e)}")
        raise e

# Function to process DataFrame in chunks for memory efficiency
@st.cache_data
def process_in_chunks(df, chunk_size, processing_func, *args, **kwargs):
    """Process a large DataFrame in chunks to avoid memory issues"""
    result_chunks = []
    total_chunks = len(df) // chunk_size + (1 if len(df) % chunk_size > 0 else 0)
    
    for i in range(0, len(df), chunk_size):
        chunk = df.iloc[i:i + chunk_size].copy()
        processed_chunk = processing_func(chunk, *args, **kwargs)
        result_chunks.append(processed_chunk)
        
        # Update progress calculation
        progress = (i + chunk_size) / len(df)
        progress = min(progress, 1.0)  # Ensure progress doesn't exceed 1.0
        yield progress, i // chunk_size + 1, total_chunks
    
    # Combine the processed chunks
    if result_chunks:
        return pd.concat(result_chunks, ignore_index=True)
    else:
        return pd.DataFrame()

# Function to create download button for dataframe
def create_download_button(df, file_name, file_format="csv", help_text=""):
    """Create appropriate download button based on file format"""
    if file_format.lower() == "csv":
        data = df.to_csv(index=False).encode('utf-8')
        mime = "text/csv"
        ext = "csv"
    elif file_format.lower() == "excel" or file_format.lower() == "xlsx":
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
            df.to_excel(writer, index=False)
        buffer.seek(0)
        data = buffer.getvalue()
        mime = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        ext = "xlsx"
    elif file_format.lower() == "json":
        data = df.to_json(orient="records", indent=2).encode('utf-8')
        mime = "application/json"
        ext = "json"
    else:
        data = df.to_csv(index=False).encode('utf-8')
        mime = "text/csv" 
        ext = "csv"
    
    st.download_button(
        label=f"Download {file_name}.{ext}",
        data=data,
        file_name=f"{file_name}.{ext}",
        mime=mime,
        help=help_text
    )

# Function to validate required columns
def validate_columns(df, required_cols, option_name):
    """Check if all required columns exist, return True/False and error message"""
    missing = [col for col in required_cols if col not in df.columns]
    if missing:
        return False, f"Required columns missing for {option_name}: {', '.join(missing)}"
    return True, ""

# Function to display file preview
def show_data_preview(df, option, max_rows=5):
    """Show a preview of the data with relevant columns highlighted"""
    st.subheader("Data Preview")
    
    # Get columns relevant to the current option
    if option == "Address + HoNWIncome" or option == "Address + HoNWIncome & Phone":
        highlight_cols = ['PERSONAL_ADDRESS', 'PERSONAL_CITY', 'PERSONAL_STATE', 
                         'HOMEOWNER', 'NET_WORTH', 'INCOME_RANGE']
        if option == "Address + HoNWIncome & Phone":
            highlight_cols.extend(['MOBILE_PHONE', 'DNC'])
    
    elif option == "ZIP Split: Address+HoNW" or option == "ZIP Split: Address+HoNW+Phone":
        highlight_cols = ['PERSONAL_ADDRESS', 'PERSONAL_CITY', 'PERSONAL_STATE', 
                         'PERSONAL_ZIP', 'HOMEOWNER', 'NET_WORTH', 'INCOME_RANGE']
        if option == "ZIP Split: Address+HoNW+Phone":
            highlight_cols.extend(['MOBILE_PHONE', 'DNC'])
    
    elif option == "Full Combined Address":
        highlight_cols = ['FIRST_NAME', 'LAST_NAME', 'PERSONAL_ADDRESS', 'PERSONAL_CITY', 
                         'PERSONAL_STATE', 'PERSONAL_ZIP']
    
    elif option == "Phone & Credit Score":
        highlight_cols = ['FIRST_NAME', 'LAST_NAME', 'PERSONAL_ADDRESS', 'PERSONAL_CITY', 
                         'PERSONAL_STATE', 'PERSONAL_ZIP', 'MOBILE_PHONE', 'DIRECT_NUMBER',
                         'SKIPTRACE_CREDIT_RATING']
    
    elif option == "Split by State":
        highlight_cols = ['PERSONAL_ADDRESS', 'PERSONAL_CITY', 'PERSONAL_STATE']
    
    elif option == "B2B Job Titles Focus":
        highlight_cols = ['FIRST_NAME', 'LAST_NAME', 'JOB_TITLE', 'COMPANY_NAME', 'COMPANY_INDUSTRY']
    
    elif option == "Filter by Zip Codes":
        highlight_cols = ['PERSONAL_ZIP']
    
    elif option == "Company Industry":
        highlight_cols = ['COMPANY_INDUSTRY']
    
    elif option == "Sha256":
        highlight_cols = ['FIRST_NAME', 'LAST_NAME', 'SHA256_PERSONAL_EMAIL', 'SHA256_BUSINESS_EMAIL']
    
    elif option == "Complete Contact Export":
        # For complete export, highlight name, address, and phone fields
        highlight_cols = ['FIRST_NAME', 'LAST_NAME', 'PERSONAL_ADDRESS', 'PERSONAL_CITY', 
                         'PERSONAL_STATE', 'PERSONAL_ZIP', 'MOBILE_PHONE', 'DIRECT_NUMBER', 'PERSONAL_PHONE']
    
    else:
        highlight_cols = df.columns[:5].tolist()  # Default to first 5 columns
    
    # Filter to only include columns that actually exist in the DataFrame
    existing_highlight_cols = [col for col in highlight_cols if col in df.columns]
    
    # Show total rows and columns
    st.write(f"Total rows: {len(df):,}, Total columns: {len(df.columns):,}")
    
    # Show highlighted columns first, then the rest
    if existing_highlight_cols:
        st.write("**Relevant columns for this operation:**")
        st.dataframe(df[existing_highlight_cols].head(max_rows), use_container_width=True)
    
    # Show a few rows of full data
    with st.expander("Full data preview"):
        st.dataframe(df.head(max_rows), use_container_width=True)
    
    # Show column info as expandable section
    with st.expander("Column information"):
        col_info = pd.DataFrame({
            'Column': df.columns,
            'Non-Null Count': df.count().values,
            'Null %': (1 - df.count() / len(df)) * 100,
            'Data Type': df.dtypes.values
        })
        st.dataframe(col_info, use_container_width=True)

# Function to create a zip file with multiple dataframes
def create_zip_download(dfs, file_names, output_format="csv"):
    """Create a ZIP file with multiple files and provide download button"""
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        for i, (file_name, df) in enumerate(zip(file_names, dfs)):
            if output_format.lower() == "csv":
                data = df.to_csv(index=False).encode('utf-8')
                mime = "text/csv"
                ext = "csv"
            elif output_format.lower() in ["excel", "xlsx"]:
                buffer = io.BytesIO()
                with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                    df.to_excel(writer, index=False)
                buffer.seek(0)
                data = buffer.getvalue()
                mime = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                ext = "xlsx"
            elif output_format.lower() == "json":
                data = df.to_json(orient="records", indent=2).encode('utf-8')
                mime = "application/json"
                ext = "json"
            else:
                data = df.to_csv(index=False).encode('utf-8')
                mime = "text/csv"
                
            zip_file.writestr(f"{file_name}.{ext}", data)
    
    zip_buffer.seek(0)
    
    st.download_button(
        label=f"Download All Files as ZIP",
        data=zip_buffer.getvalue(),
        file_name=f"address_cleaner_output.zip",
        mime="application/zip",
        key=f"download_zip_{datetime.now().strftime('%H%M%S')}",
        help="Download all processed files in a single ZIP archive"
    )

# Function to clean memory when processing large datasets
def clean_memory():
    """Attempt to free up memory after large operations"""
    gc.collect()
    
    # If psutil is available, show memory usage
    try:
        process = psutil.Process()
        memory_info = process.memory_info()
        memory_mb = memory_info.rss / 1024 / 1024
        logger.info(f"Memory usage: {memory_mb:.2f} MB")
        return memory_mb
    except ImportError:
        return None

# Main app sections
def main():
    # Setup sidebar navigation
    st.sidebar.title("📋 Control Panel")
    
    # Organize options into logical categories
    option_categories = {
        "Address Formatting": [
            "Address + HoNWIncome",
            "Address + HoNWIncome & Phone",
            "Address + HoNWIncome First Name Last Name", 
            "Business Address + First Name Last Name",
            "Full Combined Address"
        ],
        "Data Splitting": [
            "ZIP Split: Address+HoNW",
            "ZIP Split: Address+HoNW+Phone",
            "Split by State"
        ],
        "Filtering & Selection": [
            "Filter by Zip Codes",
            "Company Industry",
            "B2B Job Titles Focus"
        ],
        "Utility Tools": [
            "File Combiner and Batcher",
            "Phone & Credit Score",
            "Duplicate Analysis & Frequency Counter",
            "Sha256",
            "Complete Contact Export",
            "DNC Phone Number Cleaner"
        ]
    }
    
    # Create a flat list of all options for the backend
    all_options = ["Select an option"]
    for category in option_categories.values():
        all_options.extend(category)

    # Add category headers and options to sidebar
    selected_category = st.sidebar.radio("Select Category", list(option_categories.keys()))
    option = st.sidebar.selectbox("Select Operation", ["Select an option"] + option_categories[selected_category])
    
    # Remember user's last selection
    if option != "Select an option":
        st.session_state['user_preferences']['last_option'] = option
    
    # Settings section in sidebar
    st.sidebar.markdown("---")
    with st.sidebar.expander("⚙️ Settings"):
        # Batch size configuration
        st.session_state['user_preferences']['batch_size'] = st.number_input(
            "Split file size (rows)", 
            min_value=100, 
            max_value=10000,
            value=st.session_state['user_preferences']['batch_size'],
            step=100,
            help="Maximum number of rows in each split file"
        )
        
        # Preview settings
        st.session_state['user_preferences']['show_preview'] = st.checkbox(
            "Show data preview", 
            value=st.session_state['user_preferences']['show_preview'],
            help="Display a preview of data before processing"
        )
        
        st.session_state['user_preferences']['max_preview_rows'] = st.slider(
            "Preview rows", 
            min_value=1, 
            max_value=20, 
            value=st.session_state['user_preferences']['max_preview_rows'],
            help="Number of rows to show in the preview"
        )
        
        # Processing options
        st.session_state['user_preferences']['auto_clean_addresses'] = st.checkbox(
            "Auto-clean addresses", 
            value=st.session_state['user_preferences']['auto_clean_addresses'],
            help="Automatically clean and expand address abbreviations"
        )
        
        # Output format
        st.session_state['user_preferences']['default_output_format'] = st.selectbox(
            "Default output format",
            options=["csv", "excel", "json"],
            index=["csv", "excel", "json"].index(st.session_state['user_preferences']['default_output_format']),
            help="Default file format for downloads"
        )
    
    # Help & About section
    st.sidebar.markdown("---")
    with st.sidebar.expander("ℹ️ Help & About"):
        st.markdown("""
        **Address Cleaner** is a tool for processing and cleaning address data. 
        
        Key features:
        - Clean and format addresses
        - Split data by ZIP codes or states
        - Filter by various criteria
        - Combine and batch files
        
        For help, select an operation and see its description.
        """)
        
        st.markdown("**Version:** 2.0")
        st.markdown("**Updated:** April 2025")
    
    # Main content area
    st.title("📍 Address Cleaner Pro")

    # Description tabs
    tab1, tab2, tab3 = st.tabs(["🏠 Process", "📊 Data Visualization", "❓ FAQ"])
    
    with tab1:
        # Description based on selected option
        descriptions = {
            "Address + HoNWIncome": "Combines cleaned address with homeowner status, net worth, and income range. Includes state if available.",
            "Address + HoNWIncome & Phone": "Adds phone number to the combined data if not marked as Do Not Call (DNC). Includes state if available.",
            "Address + HoNWIncome First Name Last Name": "Combines cleaned address with homeowner status, net worth, income range, and includes first and last names for identification.",
            "Business Address + First Name Last Name": "Processes business/company addresses with cleaning and includes first and last names. Uses company address fields for business locations.",
            "ZIP Split: Address+HoNW": "Splits the cleaned address and homeowner data into separate files based on ZIP codes.",
            "ZIP Split: Address+HoNW+Phone": "Splits the cleaned address, homeowner data, and phone numbers into separate files based on ZIP codes.",
            "File Combiner and Batcher": "Combines multiple uploaded CSV files and splits the result into customizable-sized batches.",
            "Sha256": "Provides names with hashed email data, preferring personal email hash.",
            "Full Combined Address": "Generates a comprehensive dataset with full address and additional metadata.",
            "Phone & Credit Score": "Focuses on phone numbers and credit scores with address details.",
            "Duplicate Analysis & Frequency Counter": "Counts how many times each record appears, adds frequency count as first column, removes duplicates, and sorts by frequency. Useful for identifying most common records in your dataset.",
            "Split by State": "Splits the dataset into one file per state based on the PERSONAL_STATE column.",
            "B2B Job Titles Focus": "Extracts B2B job title data with company and professional details into a single file.",
            "Filter by Zip Codes": "Filters the data to include only rows where the first 5 digits of PERSONAL_ZIP match the provided 5-digit zip codes.",
            "Company Industry": "Filters data by unique industries from the COMPANY_INDUSTRY column, allowing multi-selection for efficient filtering.",
            "Complete Contact Export": "Processes and cleans the entire contact file, formatting phone numbers and addresses while preserving all original data. Maintains the original structure for compatibility with other systems.",
            "DNC Phone Number Cleaner": "Removes phone numbers from rows where the DNC column is marked 'Y' but keeps them when marked 'N'."
        }

        if option != "Select an option":
            st.info(descriptions[option])
            
            # File uploader and option-specific inputs
            if option == "File Combiner and Batcher":
                # Multiple file upload for combiner
                uploaded_files = st.file_uploader("Upload multiple CSV files", type=["csv"], accept_multiple_files=True)
                
                # Add checkbox for enabling/disabling automatic batching
                enable_batching = st.checkbox(
                    "Enable automatic batching", 
                    value=True,
                    help="When enabled, the combined file will be split into batches if it exceeds the batch size. When disabled, all files will be merged into a single file regardless of size."
                )
                
                # Only show batch size input if batching is enabled
                if enable_batching:
                    batch_size = st.number_input("Batch size (rows)", min_value=100, max_value=10000, 
                                                value=st.session_state['user_preferences']['batch_size'], step=100)
                
                if uploaded_files and st.button("Combine and Batch Files"):
                    with st.spinner("Combining files..."):
                        # Initialize combined DataFrame
                        combined_df = pd.DataFrame()
                        
                        # Show progress for each file
                        progress_bar = st.progress(0)
                        
                        # Track formats found
                        formats_detected = []
                        
                        for i, file in enumerate(uploaded_files):
                            try:
                                temp_df = pd.read_csv(file)
                                
                                # Detect and normalize format for each file
                                detected_format = detect_input_format(temp_df)
                                temp_df = normalize_dataframe(temp_df, detected_format)
                                
                                formats_detected.append(detected_format)
                                
                                combined_df = pd.concat([combined_df, temp_df], ignore_index=True)
                                progress_bar.progress((i + 1) / len(uploaded_files))
                            except Exception as e:
                                st.error(f"Error processing file {file.name}: {str(e)}")
                        
                        if combined_df.empty:
                            st.error("No data found in the uploaded files.")
                        else:
                            # Show format summary
                            format_counts = {fmt: formats_detected.count(fmt) for fmt in set(formats_detected)}
                            format_summary = []
                            for fmt, count in format_counts.items():
                                if fmt == 'old':
                                    format_summary.append(f"🔵 {count} Classic format files")
                                elif fmt == 'new':
                                    format_summary.append(f"🟢 {count} Enhanced format files")
                                else:
                                    format_summary.append(f"🟡 {count} Unknown format files")
                            
                            st.info(f"📁 Combined files: {', '.join(format_summary)}")
                            st.success(f"✅ Combined {len(uploaded_files)} files with {len(combined_df):,} total rows")
                            
                            # Show preview of combined data
                            if st.session_state['user_preferences']['show_preview']:
                                show_data_preview(combined_df, option, 
                                                max_rows=st.session_state['user_preferences']['max_preview_rows'])
                            
                            # Determine if batching is needed based on checkbox
                            needs_batching = enable_batching and len(combined_df) > batch_size if enable_batching else False
                            
                            if needs_batching:
                                # Split into batches
                                batched_dfs = split_dataframe(combined_df, batch_size)
                                
                                st.success(f"✅ Data split into {len(batched_dfs)} batches of {batch_size:,} rows each")
                                
                                # Prepare file names
                                file_names = [f"batch_{i+1}" for i in range(len(batched_dfs))]
                                
                                # Create download options
                                output_format = st.radio("Output format:", 
                                                       ("CSV", "Excel", "JSON"), 
                                                       horizontal=True)
                                
                                # ZIP download for all batches
                                create_zip_download(batched_dfs, file_names, output_format.lower())
                                
                                # Individual batch downloads
                                with st.expander("Download individual batches"):
                                    batch_cols = st.columns(3)  # 3 columns for batch downloads
                                    for i, (file_name, df_part) in enumerate(zip(file_names, batched_dfs)):
                                        with batch_cols[i % 3]:  # Distribute across columns
                                            create_download_button(
                                                df_part, 
                                                file_name, 
                                                output_format.lower(), 
                                                f"Download batch {i+1} with {len(df_part):,} rows"
                                            )
                            else:
                                # Single file download
                                if enable_batching:
                                    st.info(f"ℹ️ File contains {len(combined_df):,} rows which is below the batch size of {batch_size:,} rows. No batching needed.")
                                else:
                                    st.info("ℹ️ Automatic batching is disabled. All files merged into a single file.")
                                
                                output_format = st.radio("Output format:", 
                                                       ("CSV", "Excel", "JSON"), 
                                                       horizontal=True)
                                
                                create_download_button(
                                    combined_df, 
                                    "combined_data", 
                                    output_format.lower(), 
                                    f"Download combined file with {len(combined_df):,} rows"
                                )
            else:
                # Single file upload for other options
                uploaded_file = st.file_uploader("Upload your CSV file", type=["csv"], 
                                               help="Maximum recommended file size: 200MB")
                
                # Additional inputs based on option
                if option == "Filter by Zip Codes":
                    zip_codes_input = st.text_area(
                        "Enter 5-digit zip codes (separated by spaces, commas, or newlines)",
                        height=100,
                        help="Example: 90210 60601 10001"
                    )
                
                elif option in ["ZIP Split: Address+HoNW", "ZIP Split: Address+HoNW+Phone"]:
                    zip_filter_input = st.text_area(
                        "Optionally enter zip codes to filter (leave empty to include all):",
                        height=100,
                        help="Example: 90210 60601 10001"
                    )
                
                # Company Industry specific inputs
                elif option == "Company Industry":
                    # Handle Company Industry option separately
                    if uploaded_file:
                        # Read and process the file for Company Industry filtering
                        try:
                            df = pd.read_csv(uploaded_file)
                            
                            # Detect and normalize format
                            detected_format = detect_input_format(df)
                            df = normalize_dataframe(df, detected_format)
                            
                            # Display format information
                            if detected_format == 'old':
                                format_class = "format-old"
                                format_emoji = "🔵"
                            elif detected_format == 'new':
                                format_class = "format-new"
                                format_emoji = "🟢"
                            else:
                                format_class = "format-unknown"
                                format_emoji = "🟡"
                            
                            st.markdown(f"""
                            <div class="format-indicator {format_class}">
                                {format_emoji} <strong>Format Detected:</strong> {detected_format.title()} format<br>
                                <small>📊 {len(df):,} rows, {len(df.columns):,} columns</small>
                            </div>
                            """, unsafe_allow_html=True)
                            
                            # Check for COMPANY_INDUSTRY column
                            if 'COMPANY_INDUSTRY' not in df.columns:
                                st.error("CSV file must contain 'COMPANY_INDUSTRY' column for industry filtering.")
                            else:
                                # Get unique industries
                                unique_industries = df['COMPANY_INDUSTRY'].dropna().unique()
                                unique_industries = [industry for industry in unique_industries if str(industry).strip() != '']
                                
                                if len(unique_industries) == 0:
                                    st.warning("No valid industries found in the COMPANY_INDUSTRY column.")
                                else:
                                    st.write(f"Found {len(unique_industries)} unique industries in your data:")
                                    
                                    # Multi-select for industries
                                    selected_industries = st.multiselect(
                                        "Select industries to include in the filtered data:",
                                        options=sorted(unique_industries),
                                        default=None,
                                        help="Select one or more industries to filter your data"
                                    )
                                    
                                    # Show industry distribution
                                    with st.expander("Industry Distribution"):
                                        industry_counts = df['COMPANY_INDUSTRY'].value_counts()
                                        st.dataframe(pd.DataFrame({
                                            'Industry': industry_counts.index,
                                            'Count': industry_counts.values
                                        }), use_container_width=True)
                                    
                                    # Process the filtering
                                    if selected_industries and st.button("Filter by Selected Industries"):
                                        with st.spinner("Filtering data by selected industries..."):
                                            # Filter the data
                                            filtered_df = df[df['COMPANY_INDUSTRY'].isin(selected_industries)]
                                            
                                            st.success(f"✅ Filtering complete! Found {len(filtered_df):,} rows matching selected industries")
                                            st.write(f"Filter matched {len(filtered_df) / len(df) * 100:.1f}% of original data")
                                            
                                            # Show breakdown by selected industries
                                            filtered_industry_counts = filtered_df['COMPANY_INDUSTRY'].value_counts()
                                            st.write("**Records by Selected Industry:**")
                                            st.dataframe(pd.DataFrame({
                                                'Industry': filtered_industry_counts.index,
                                                'Count': filtered_industry_counts.values
                                            }), use_container_width=True)
                                            
                                            # Show preview if enabled
                                            if st.session_state['user_preferences']['show_preview']:
                                                show_data_preview(filtered_df, option, 
                                                                max_rows=st.session_state['user_preferences']['max_preview_rows'])
                                            
                                            # Provide download options
                                            output_format = st.radio("Output format:", 
                                                                   ("CSV", "Excel", "JSON"), 
                                                                   horizontal=True)
                                            
                                            create_download_button(
                                                filtered_df,
                                                "filtered_by_industry",
                                                output_format.lower(),
                                                f"Download {len(filtered_df):,} records filtered by industry"
                                            )
                                    
                                    elif not selected_industries:
                                        st.info("Please select at least one industry to filter the data.")
                        
                        except Exception as e:
                            st.error(f"Error processing file: {str(e)}")
                    
                # Process button for all other options (excluding Company Industry which is handled above)
                if uploaded_file and option not in ["Company Industry"]:
                    # Initialize session state for main processing if not exists
                    if 'main_processing' not in st.session_state:
                        st.session_state['main_processing'] = {
                            'processed': False,
                            'current_option': None,
                            'df': None,
                            'format_info': None
                        }
                    
                    # Check if option changed
                    if st.session_state['main_processing']['current_option'] != option:
                        st.session_state['main_processing']['processed'] = False
                        st.session_state['main_processing']['current_option'] = option
                        st.session_state['main_processing']['df'] = None
                        st.session_state['main_processing']['format_info'] = None
                    
                    # Process Data button
                    process_clicked = st.button("Process Data", key="main_process_btn")
                    
                    # Processing logic
                    if process_clicked or st.session_state['main_processing']['processed']:
                        if process_clicked:
                            st.session_state['main_processing']['processed'] = False
                        
                        if not st.session_state['main_processing']['processed']:
                            with st.spinner("Processing file..."):
                                # Read the uploaded file
                                try:
                                    df = pd.read_csv(uploaded_file)
                                    
                                    # Detect input format
                                    detected_format = detect_input_format(df)
                                    format_info = get_format_info(df, detected_format)
                                    
                                    # Display format information
                                    if detected_format == 'old':
                                        format_class = "format-old"
                                        format_emoji = "🔵"
                                    elif detected_format == 'new':
                                        format_class = "format-new"
                                        format_emoji = "🟢"
                                    else:
                                        format_class = "format-unknown"
                                        format_emoji = "🟡"
                                    
                                    st.markdown(f"""
                                    <div class="format-indicator {format_class}">
                                        {format_emoji} <strong>Format Detected:</strong> {format_info['description']}<br>
                                        <small>📊 {format_info['total_rows']:,} rows, {format_info['total_columns']:,} columns</small>
                                    </div>
                                    """, unsafe_allow_html=True)
                                    
                                    # Normalize the DataFrame
                                    df = normalize_dataframe(df, detected_format)
                                    
                                    st.success(f"File loaded and normalized with {len(df):,} rows and {len(df.columns):,} columns")
                                    
                                    # Store the normalized data in session state for visualization
                                    st.session_state['processed_data'] = df.copy()
                                    
                                    # Store processing results in session state
                                    st.session_state['main_processing']['df'] = df
                                    st.session_state['main_processing']['format_info'] = format_info
                                    st.session_state['main_processing']['processed'] = True
                                    
                                except Exception as e:
                                    st.error(f"Error reading file: {str(e)}")
                                    st.stop()
                        
                        # Use stored data from session state
                        if st.session_state['main_processing']['df'] is not None:
                            df = st.session_state['main_processing']['df']
                            format_info = st.session_state['main_processing']['format_info']
                            
                            # Show format-specific features
                            with st.expander("Format Details"):
                                st.write("**Key Features:**")
                                for feature in format_info['key_features']:
                                    st.write(f"• {feature}")
                                
                                if format_info['format'] == 'new':
                                    new_cols_present = [col for col in NEW_FORMAT_SPECIFIC_COLUMNS if col in df.columns]
                                    if new_cols_present:
                                        st.write("**Enhanced columns available:**")
                                        st.write(", ".join(new_cols_present))
                            
                            # Show preview if enabled
                            if st.session_state['user_preferences']['show_preview']:
                                show_data_preview(df, option, 
                                                max_rows=st.session_state['user_preferences']['max_preview_rows'])
                            

                            # Validate required columns based on option
                            if option == "Filter by Zip Codes":
                                valid, msg = validate_columns(df, ['PERSONAL_ZIP'], option)
                            elif option == "Address + HoNWIncome":
                                valid, msg = validate_columns(df, ['PERSONAL_ADDRESS', 'PERSONAL_CITY'], option)
                            elif option == "Address + HoNWIncome & Phone":
                                valid, msg = validate_columns(df, ['PERSONAL_ADDRESS', 'PERSONAL_CITY', 'MOBILE_PHONE'], option)
                                # Note: DNC column is now created during normalization if missing
                            elif option == "Address + HoNWIncome First Name Last Name":
                                valid, msg = validate_columns(df, ['FIRST_NAME', 'LAST_NAME', 'PERSONAL_ADDRESS', 'PERSONAL_CITY'], option)
                            elif option == "Business Address + First Name Last Name":
                                # Check for business address columns - prefer COMPANY_ADDRESS, fall back to PROFESSIONAL_ADDRESS
                                if 'COMPANY_ADDRESS' in df.columns:
                                    valid, msg = validate_columns(df, ['FIRST_NAME', 'LAST_NAME', 'COMPANY_ADDRESS'], option)
                                elif 'PROFESSIONAL_ADDRESS' in df.columns:
                                    valid, msg = validate_columns(df, ['FIRST_NAME', 'LAST_NAME', 'PROFESSIONAL_ADDRESS'], option)
                                else:
                                    valid = False
                                    msg = "CSV file must contain either 'COMPANY_ADDRESS' or 'PROFESSIONAL_ADDRESS' for business address processing."
                            elif option == "Sha256":
                                # For SHA256, check for either format's email columns
                                required_cols = ['FIRST_NAME', 'LAST_NAME']
                                email_cols = ['SHA256_PERSONAL_EMAIL', 'SHA256_BUSINESS_EMAIL']
                                valid, msg = validate_columns(df, required_cols, option)
                                if valid and not any(col in df.columns for col in email_cols):
                                    valid = False
                                    msg = f"CSV file must contain at least one of: {', '.join(email_cols)}"
                            elif option == "Full Combined Address":
                                valid, msg = validate_columns(df, ['FIRST_NAME', 'LAST_NAME', 'PERSONAL_ADDRESS', 'PERSONAL_CITY', 'PERSONAL_STATE', 'PERSONAL_ZIP'], option)
                            elif option == "Phone & Credit Score":
                                valid, msg = validate_columns(df, ['FIRST_NAME', 'LAST_NAME', 'PERSONAL_ADDRESS', 'PERSONAL_CITY', 'PERSONAL_STATE', 'PERSONAL_ZIP'], option)
                                # Special check for phone number columns
                                if valid and 'MOBILE_PHONE' not in df.columns and 'DIRECT_NUMBER' not in df.columns:
                                    valid = False
                                    msg = "CSV file must contain at least one of 'MOBILE_PHONE' or 'DIRECT_NUMBER'."
                            elif option == "Duplicate Analysis & Frequency Counter":
                                # No specific column requirements - can work with any CSV data
                                valid = True
                                msg = ""
                            elif option == "Split by State":
                                valid, msg = validate_columns(df, ['PERSONAL_ADDRESS', 'PERSONAL_CITY', 'PERSONAL_STATE'], option)
                            elif option == "B2B Job Titles Focus":
                                valid, msg = validate_columns(df, ['JOB_TITLE'], option)
                            elif option in ["ZIP Split: Address+HoNW", "ZIP Split: Address+HoNW+Phone"]:
                                valid, msg = validate_columns(df, ['PERSONAL_ADDRESS', 'PERSONAL_CITY', 'PERSONAL_STATE', 'PERSONAL_ZIP'], option)
                            elif option == "Complete Contact Export":
                                # No specific column requirements for complete export - accepts any valid CSV
                                valid = True
                                msg = ""
                            elif option == "DNC Phone Number Cleaner":
                                # Check for DNC columns
                                dnc_cols = [col for col in df.columns if 'DNC' in col.upper()]
                                if not dnc_cols:
                                    valid = False
                                    msg = "CSV file must contain at least one column with 'DNC' in the name."
                                else:
                                    valid = True
                                    msg = ""
                            else:
                                valid = True
                                msg = ""
                            

                            if not valid:
                                st.error(msg)
                            else:
                                # Process data based on selected option
                                processing_container = st.container()
                                progress_bar = st.progress(0)
                                processing_text = st.empty()
                                
                                # Set up tracking for timed progress updates
                                start_time = time.time()
                                total_steps = 6  # Adjust based on processing steps
                                
                                # Process based on option (continuing with original logic structure, but improved)
                                # This is where we'll implement the option-specific processing
                                
                                # SHA256 OPTION
                                if option == "Sha256":
                                    processing_text.text("Processing SHA256 email data...")
                                    
                                    # Create output DataFrame with names and email hashes
                                    output_df = df[['FIRST_NAME', 'LAST_NAME']].copy()
                                    
                                    # Handle email hash preference - prefer personal over business
                                    if 'SHA256_PERSONAL_EMAIL' in df.columns and 'SHA256_BUSINESS_EMAIL' in df.columns:
                                        # Use personal email hash if available, otherwise business email hash
                                        output_df['EMAIL_HASH'] = df['SHA256_PERSONAL_EMAIL'].fillna(df['SHA256_BUSINESS_EMAIL'])
                                    elif 'SHA256_PERSONAL_EMAIL' in df.columns:
                                        output_df['EMAIL_HASH'] = df['SHA256_PERSONAL_EMAIL']
                                    elif 'SHA256_BUSINESS_EMAIL' in df.columns:
                                        output_df['EMAIL_HASH'] = df['SHA256_BUSINESS_EMAIL']
                                    else:
                                        st.error("No SHA256 email columns found.")
                                    
                                    # Remove rows where email hash is empty
                                    output_df = output_df[output_df['EMAIL_HASH'].notna() & (output_df['EMAIL_HASH'] != '')]
                                    
                                    progress_bar.progress(0.6)
                                    
                                    st.success(f"✅ Processing complete! Generated {len(output_df):,} rows with email hashes")
                                    
                                    # Show hash statistics
                                    if 'SHA256_PERSONAL_EMAIL' in df.columns and 'SHA256_BUSINESS_EMAIL' in df.columns:
                                        personal_hashes = sum(df['SHA256_PERSONAL_EMAIL'].notna() & (df['SHA256_PERSONAL_EMAIL'] != ''))
                                        business_hashes = sum(df['SHA256_BUSINESS_EMAIL'].notna() & (df['SHA256_BUSINESS_EMAIL'] != ''))
                                        st.write(f"**Personal email hashes:** {personal_hashes:,}")
                                        st.write(f"**Business email hashes:** {business_hashes:,}")
                                    
                                    # Provide download options
                                    output_format = st.radio("Output format:", 
                                                           ("CSV", "Excel", "JSON"), 
                                                           horizontal=True)
                                    
                                    create_download_button(
                                        output_df,
                                        "sha256_emails",
                                        output_format.lower(),
                                        f"Download {len(output_df):,} records with email hashes"
                                    )
                                    
                                    progress_bar.progress(1.0)
                                
                                # SPLIT BY STATE
                                elif option == "Split by State":
                                    processing_text.text("Processing state-based split...")
                                    
                                    # Clean addresses if requested
                                    if st.session_state['user_preferences']['auto_clean_addresses']:
                                        df = df[df['PERSONAL_ADDRESS'].notna()]
                                        df['PERSONAL_ADDRESS_CLEAN'] = df['PERSONAL_ADDRESS'].apply(clean_address)
                                        progress_bar.progress(0.2)
                                    
                                    # Group by state
                                    state_groups = []
                                    state_file_names = []
                                    
                                    processing_text.text("Creating separate files for each state...")
                                    
                                    for state, group in df.groupby('PERSONAL_STATE'):
                                        if pd.notna(state) and state.strip() != '':
                                            state_groups.append(group)
                                            state_file_names.append(f"state_{state.strip()}")
                                    
                                    progress_bar.progress(0.8)
                                    
                                    # Show results
                                    st.success(f"✅ Processing complete! Split data into {len(state_groups)} state groups")
                                    
                                    # Create a summary of the states
                                    state_summary = pd.DataFrame({
                                        'State': df['PERSONAL_STATE'].value_counts().index,
                                        'Record Count': df['PERSONAL_STATE'].value_counts().values
                                    })
                                    
                                    st.write("**State Distribution:**")
                                    st.dataframe(state_summary, use_container_width=True)
                                    
                                    # Provide download options
                                    output_format = st.radio("Output format:", 
                                                           ("CSV", "Excel", "JSON"), 
                                                           horizontal=True)
                                    
                                    # ZIP download for all files
                                    create_zip_download(state_groups, state_file_names, output_format.lower())
                                    
                                    # Option to download individual state files
                                    with st.expander("Download individual state files"):
                                        # Create a multiselect to choose which states to download
                                        selected_states = st.multiselect(
                                            "Select states to download individually:",
                                            options=df['PERSONAL_STATE'].value_counts().index.tolist(),
                                            default=None,
                                            help="Select states to download as individual files"
                                        )
                                        
                                        if selected_states:
                                            state_cols = st.columns(3)  # 3 columns for download buttons
                                            for i, state in enumerate(selected_states):
                                                with state_cols[i % 3]:
                                                    state_df = df[df['PERSONAL_STATE'] == state]
                                                    
                                                    create_download_button(
                                                        state_df,
                                                        f"state_{state}",
                                                        output_format.lower(),
                                                        f"Download {state} ({len(state_df):,} records)"
                                                    )
                                    
                                    progress_bar.progress(1.0)
                                
                                # B2B JOB TITLES FOCUS
                                elif option == "B2B Job Titles Focus":
                                    processing_text.text("Processing B2B job title data...")
                                    
                                    # Filter for rows with job titles
                                    b2b_df = df[df['JOB_TITLE'].notna() & (df['JOB_TITLE'] != '')].copy()
                                    
                                    # Select relevant B2B columns
                                    b2b_columns = ['FIRST_NAME', 'LAST_NAME', 'JOB_TITLE', 'COMPANY_NAME', 'COMPANY_INDUSTRY']
                                    
                                    # Add optional columns if they exist
                                    optional_columns = ['DEPARTMENT', 'SENIORITY_LEVEL', 'LINKEDIN_URL', 'BUSINESS_EMAIL', 
                                                      'COMPANY_DOMAIN', 'COMPANY_PHONE', 'COMPANY_ADDRESS']
                                    
                                    for col in optional_columns:
                                        if col in b2b_df.columns:
                                            b2b_columns.append(col)
                                    
                                    # Create output with available columns
                                    available_columns = [col for col in b2b_columns if col in b2b_df.columns]
                                    output_df = b2b_df[available_columns].copy()
                                    
                                    progress_bar.progress(0.6)
                                    
                                    st.success(f"✅ Processing complete! Extracted {len(output_df):,} B2B records")
                                    
                                    # Show job title statistics
                                    top_titles = output_df['JOB_TITLE'].value_counts().head(10)
                                    st.write("**Top 10 Job Titles:**")
                                    st.dataframe(pd.DataFrame({
                                        'Job Title': top_titles.index,
                                        'Count': top_titles.values
                                    }), use_container_width=True)
                                    
                                    if 'COMPANY_INDUSTRY' in output_df.columns:
                                        top_industries = output_df['COMPANY_INDUSTRY'].value_counts().head(10)
                                        st.write("**Top 10 Industries:**")
                                        st.dataframe(pd.DataFrame({
                                            'Industry': top_industries.index,
                                            'Count': top_industries.values
                                        }), use_container_width=True)
                                    
                                    # Provide download options
                                    output_format = st.radio("Output format:", 
                                                           ("CSV", "Excel", "JSON"), 
                                                           horizontal=True)
                                    
                                    create_download_button(
                                        output_df,
                                        "b2b_job_titles",
                                        output_format.lower(),
                                        f"Download {len(output_df):,} B2B records"
                                    )
                                    
                                    progress_bar.progress(1.0)
                                
                                # FILTER BY ZIP CODES
                                elif option == "Filter by Zip Codes":
                                    if zip_codes_input:
                                        processing_text.text("Filtering by zip codes...")
                                        
                                        # Ensure PERSONAL_ZIP is string to preserve leading zeros
                                        df['PERSONAL_ZIP'] = df['PERSONAL_ZIP'].astype(str)
                                        
                                        # Create temporary column with first 5 digits, stripping spaces
                                        df['PERSONAL_ZIP_5'] = df['PERSONAL_ZIP'].fillna('').astype(str).str.strip().str[:5]
                                        
                                        # Parse input zip codes
                                        zip_codes = [str(zip_code).strip()[:5] for zip_code in 
                                                    zip_codes_input.replace(",", " ").split() 
                                                    if str(zip_code).strip()]
                                        
                                        progress_bar.progress(0.3)
                                        
                                        if not zip_codes:
                                            st.error("No valid zip codes provided.")
                                        else:
                                            # Filter the DataFrame
                                            filtered_df = df[df['PERSONAL_ZIP_5'].isin(zip_codes)]
                                            filtered_df = filtered_df.drop(columns=['PERSONAL_ZIP_5'])
                                            
                                            progress_bar.progress(0.6)
                                            
                                            # Show filter results
                                            st.write(f"Found {len(filtered_df):,} rows matching the zip codes")
                                            st.write(f"Filter matched {len(filtered_df) / len(df) * 100:.1f}% of original data")
                                            
                                            # Debug info for zip code matching
                                            with st.expander("Filter Details"):
                                                st.write("**Zip Codes Used for Filtering:**", ", ".join(zip_codes))
                                                st.write("**Unique PERSONAL_ZIP (first 5 digits) in Data:**", 
                                                        ", ".join(sorted(df['PERSONAL_ZIP_5'].unique().tolist())[:25]) + 
                                                        ("..." if len(df['PERSONAL_ZIP_5'].unique()) > 25 else ""))
                                            

                                            # Provide download options if we have results
                                            if not filtered_df.empty:
                                                output_format = st.radio("Output format:", 
                                                                      ("CSV", "Excel", "JSON"), 
                                                                      horizontal=True)
                                                
                                                create_download_button(
                                                    filtered_df, 
                                                    "filtered_by_zip_codes", 
                                                    output_format.lower(),
                                                    f"Download {len(filtered_df):,} filtered records"
                                                )
                                                
                                                st.success("✅ Filtering complete!")
                                            else:
                                                st.warning("No rows match the provided zip codes. Please check your input.")
                                        
                                        progress_bar.progress(1.0)
                                    else:
                                        st.error("Please enter zip codes to filter.")
                                
                                # ZIP SPLIT: ADDRESS+HONW
                                elif option == "ZIP Split: Address+HoNW":
                                    processing_text.text("Processing addresses and preparing ZIP code split...")
                                    
                                    # Clean the data
                                    if st.session_state['user_preferences']['auto_clean_addresses']:
                                        df = df[df['PERSONAL_ADDRESS'].notna()]
                                        df['PERSONAL_ADDRESS_CLEAN'] = df['PERSONAL_ADDRESS'].apply(clean_address)
                                        progress_bar.progress(0.2)
                                    
                                    # Create the address field
                                    df['ADDRESS'] = df[['PERSONAL_ADDRESS_CLEAN', 'PERSONAL_CITY', 'PERSONAL_STATE']].apply(
                                        lambda row: ', '.join([str(x) for x in row if pd.notna(x) and x != '']), axis=1
                                    )
                                    
                                    # Handle missing values
                                    df['HOMEOWNER'] = df['HOMEOWNER'].fillna('')
                                    df['NET_WORTH'] = df['NET_WORTH'].fillna('')
                                    df['INCOME_RANGE'] = df['INCOME_RANGE'].fillna('')
                                    
                                    # Create the data field
                                    df['DATA'] = 'Ho ' + df['HOMEOWNER'] + ' | NW ' + df['NET_WORTH'] + ' | Income ' + df['INCOME_RANGE']
                                    
                                    progress_bar.progress(0.4)
                                    
                                    # Filter by ZIP codes if specified
                                    if 'zip_filter_input' in locals() and zip_filter_input.strip():
                                        zip_codes = [z.strip() for z in zip_filter_input.replace(",", " ").split() if z.strip()]
                                        df['PERSONAL_ZIP'] = df['PERSONAL_ZIP'].fillna('').astype(str).str.strip()
                                        df = df[df['PERSONAL_ZIP'].str[:5].isin(zip_codes)]
                                        processing_text.text(f"Filtered to {len(df):,} rows matching the specified ZIP codes")
                                    
                                    progress_bar.progress(0.6)
                                    
                                    # Group by ZIP code
                                    zip_groups = []
                                    zip_file_names = []
                                    
                                    processing_text.text("Creating separate files for each ZIP code...")
                                    
                                    # Group the data by ZIP code
                                    for zip_code, group in df.groupby('PERSONAL_ZIP'):
                                        # Only include address and data in output
                                        output_group = group[['ADDRESS', 'DATA']]
                                        zip_groups.append(output_group)
                                        zip_file_names.append(f"zip_{zip_code}")
                                    
                                    progress_bar.progress(0.8)
                                    
                                    # Show results
                                    st.success(f"✅ Processing complete! Split data into {len(zip_groups)} ZIP code groups")
                                    
                                    # Create a summary of the ZIP codes
                                    zip_summary = pd.DataFrame({
                                        'ZIP Code': df['PERSONAL_ZIP'].unique(),
                                        'Record Count': [len(df[df['PERSONAL_ZIP'] == z]) for z in df['PERSONAL_ZIP'].unique()]
                                    }).sort_values('Record Count', ascending=False)
                                    
                                    st.write("**ZIP Code Distribution:**")
                                    st.dataframe(zip_summary, use_container_width=True)
                                    
                                    # Provide download options
                                    output_format = st.radio("Output format:", 
                                                           ("CSV", "Excel", "JSON"), 
                                                           horizontal=True)
                                    
                                    # ZIP download for all files
                                    create_zip_download(zip_groups, zip_file_names, output_format.lower())
                                    
                                    # Option to download individual ZIP files
                                    with st.expander("Download individual ZIP files"):
                                        # Create a multiselect to choose which ZIP codes to download
                                        selected_zips = st.multiselect(
                                            "Select ZIP codes to download individually:",
                                            options=df['PERSONAL_ZIP'].unique(),
                                            default=None,
                                            help="Select ZIP codes to download as individual files"
                                        )
                                        
                                        if selected_zips:
                                            # Filter to only the selected ZIP codes
                                            selected_indices = [i for i, zip_code in enumerate(df['PERSONAL_ZIP'].unique()) 
                                                                  if zip_code in selected_zips]
                                            

                                            zip_cols = st.columns(3)  # 3 columns for download buttons
                                            for i, idx in enumerate(selected_indices):
                                                with zip_cols[i % 3]:
                                                    zip_code = df['PERSONAL_ZIP'].unique()[idx]
                                                    group_df = df[df['PERSONAL_ZIP'] == zip_code][['ADDRESS', 'DATA']]
                                                    
                                                    create_download_button(
                                                        group_df,
                                                        f"zip_{zip_code}",
                                                        output_format.lower(),
                                                        f"Download ZIP {zip_code} ({len(group_df):,} records)"
                                                    )
                                                
                                        progress_bar.progress(1.0)
                                
                                # ZIP SPLIT: ADDRESS+HONW+PHONE
                                elif option == "ZIP Split: Address+HoNW+Phone":
                                    processing_text.text("Processing addresses with phone data and preparing ZIP code split...")
                                    
                                    # Clean the data
                                    if st.session_state['user_preferences']['auto_clean_addresses']:
                                        df = df[df['PERSONAL_ADDRESS'].notna()]
                                        df['PERSONAL_ADDRESS_CLEAN'] = df['PERSONAL_ADDRESS'].apply(clean_address)
                                        progress_bar.progress(0.2)
                                    
                                    # Create the address field
                                    df['ADDRESS'] = df[['PERSONAL_ADDRESS_CLEAN', 'PERSONAL_CITY', 'PERSONAL_STATE']].apply(
                                        lambda row: ', '.join([str(x) for x in row if pd.notna(x) and x != '']), axis=1
                                    )
                                    
                                    # Handle missing values
                                    df['MOBILE_PHONE'] = df['MOBILE_PHONE'].fillna('')
                                    df['DNC'] = df['DNC'].fillna('N')
                                    df['HOMEOWNER'] = df['HOMEOWNER'].fillna('')
                                    df['NET_WORTH'] = df['NET_WORTH'].fillna('')
                                    df['INCOME_RANGE'] = df['INCOME_RANGE'].fillna('')
                                    
                                    # Format phone numbers if needed
                                    if st.session_state['user_preferences'].get('format_phone_numbers', True):
                                        df['MOBILE_PHONE'] = df['MOBILE_PHONE'].apply(validate_phone)
                                    
                                    # Create the data field with phone numbers for non-DNC records
                                    df['DATA'] = 'Ho ' + df['HOMEOWNER'] + ' | NW ' + df['NET_WORTH'] + ' | Income ' + df['INCOME_RANGE'] + \
                                            df.apply(lambda row: ' | Phone ' + str(row['MOBILE_PHONE']) if (
                                                    row['DNC'] != 'Y' and row['MOBILE_PHONE'] != '') else '', axis=1)
                                    
                                    # Final output
                                    output_df = df[['ADDRESS', 'DATA']]
                                    
                                    progress_bar.progress(0.6)
                                    
                                    # Check if we need to split the output
                                    batch_size = st.session_state['user_preferences']['batch_size']
                                    if len(output_df) > batch_size:
                                        processing_text.text(f"Splitting output into batches (max {batch_size:,} rows per file)...")
                                        
                                        # Split the DataFrame
                                        output_batches = split_dataframe(output_df, batch_size)
                                        batch_names = [f"address_honwincome_phone_part_{i+1}" for i in range(len(output_batches))]
                                        
                                        st.success(f"✅ Processing complete! Split into {len(output_batches)} batches")
                                        
                                        # Add stats about phone numbers
                                        total_phones = len(df[df['MOBILE_PHONE'] != ''])
                                        callable_phones = len(df[(df['MOBILE_PHONE'] != '') & (df['DNC'] != 'Y')])
                                        
                                        st.write(f"**Total records with phone numbers:** {total_phones:,} ({total_phones/len(df)*100:.1f}%)")
                                        st.write(f"**Callable phone numbers (not DNC):** {callable_phones:,} ({callable_phones/len(df)*100:.1f}%)")
                                        
                                        # Provide download options
                                        output_format = st.radio("Output format:", 
                                                               ("CSV", "Excel", "JSON"), 
                                                               horizontal=True)
                                        
                                        # ZIP download for all batches
                                        create_zip_download(output_batches, batch_names, output_format.lower())
                                        
                                        # Individual batch downloads
                                        with st.expander("Download individual batches"):
                                            batch_cols = st.columns(3)  # 3 columns for batch downloads
                                            for i, (batch_name, batch_df) in enumerate(zip(batch_names, output_batches)):
                                                with batch_cols[i % 3]:  # Alternate between columns
                                                    create_download_button(
                                                        batch_df,
                                                        batch_name,
                                                        output_format.lower(),
                                                        f"Download batch {i+1} with {len(batch_df):,} rows"
                                                    )
                                    else:
                                        st.success(f"✅ Processing complete! Generated {len(output_df):,} rows")
                                        
                                        # Add stats about phone numbers
                                        total_phones = len(df[df['MOBILE_PHONE'] != ''])
                                        callable_phones = len(df[(df['MOBILE_PHONE'] != '') & (df['DNC'] != 'Y')])
                                        
                                        st.write(f"**Total records with phone numbers:** {total_phones:,} ({total_phones/len(df)*100:.1f}%)")
                                        st.write(f"**Callable phone numbers (not DNC):** {callable_phones:,} ({callable_phones/len(df)*100:.1f}%)")
                                        
                                        # Provide download options
                                        output_format = st.radio("Output format:", 
                                                               ("CSV", "Excel", "JSON"), 
                                                               horizontal=True)
                                        
                                        # Single file download
                                        create_download_button(
                                            output_df,
                                            "address_honwincome_phone",
                                            output_format.lower(),
                                            f"Download processed data with {len(output_df):,} rows"
                                        )
                                        
                                    # Add Google My Maps instructions
                                    with st.expander("How to Import into Google My Maps"):
                                        st.markdown("""
                                        ### How to Import into Google My Maps:
                                        1. Go to [Google My Maps](https://www.google.com/mymaps).
                                        2. Click **Create a new map**.
                                        3. In the new map, click **Import** under the layer section.
                                        4. Upload the downloaded CSV file(s) or extract from ZIP.
                                        5. Set the following:
                                           - **Placemarker Pins**: Select the `ADDRESS` column.
                                           - **Placemarker Name (Title)**: Select the `DATA` column.
                                        6. Dismiss any locations that result in an error during import.
                                        7. Zoom out and manually delete any pins that are significantly distant from the main cluster.
                                        """)
                                    
                                    progress_bar.progress(1.0)
                                
                                # DNC PHONE NUMBER CLEANER (SIMPLIFIED)
                                elif option == "DNC Phone Number Cleaner":
                                    processing_text.text("Processing DNC phone number cleaning...")
                                    
                                    # Make a copy to avoid modifying the original
                                    output_df = df.copy()
                                    
                                    # Find all potential DNC columns
                                    potential_dnc_cols = [col for col in output_df.columns if 'DNC' in col.upper()]
                                    
                                    if not potential_dnc_cols:
                                        st.error("No DNC columns found in the dataset. Please ensure your data contains columns with 'DNC' in the name.")
                                    else:
                                        # Configuration Section
                                        st.subheader("DNC Processing Setup")
                                        
                                        # Map phone columns to their corresponding DNC columns
                                        phone_dnc_mapping = {
                                            'MOBILE_PHONE': 'MOBILE_PHONE_DNC',
                                            'DIRECT_NUMBER': 'DIRECT_DNC',
                                            'PERSONAL_PHONE': 'PERSONAL_PHONE_DNC',
                                            'COMPANY_PHONE': 'COMPANY_PHONE_DNC',
                                            'SKIPTRACE_B2B_PHONE': 'SKIPTRACE_B2B_PHONE_DNC'
                                        }
                                        
                                        # Identify available phone columns and their matching DNC columns
                                        available_pairs = []
                                        for phone_col, dnc_col in phone_dnc_mapping.items():
                                            if phone_col in output_df.columns and dnc_col in output_df.columns:
                                                available_pairs.append((phone_col, dnc_col))
                                        
                                        if not available_pairs:
                                            st.warning("⚠️ No matching phone/DNC column pairs found. Looking for pairs like MOBILE_PHONE/MOBILE_PHONE_DNC.")
                                            st.info("Available DNC columns: " + ", ".join(potential_dnc_cols))
                                        else:
                                            # Show what will be processed
                                            with st.expander("Phone/DNC Column Pairs to Process"):
                                                for phone_col, dnc_col in available_pairs:
                                                    st.write(f"- **{phone_col}** → checked against **{dnc_col}**")
                                        
                                        # Show data preview before processing
                                        with st.expander("📊 Data Preview Before Processing"):
                                            st.write("**First 5 rows showing phone and DNC columns:**")
                                            preview_cols = []
                                            for phone_col, dnc_col in available_pairs:
                                                preview_cols.extend([phone_col, dnc_col])
                                            if 'FIRST_NAME' in output_df.columns:
                                                preview_cols = ['FIRST_NAME', 'LAST_NAME'] + preview_cols
                                            available_preview_cols = [col for col in preview_cols if col in output_df.columns]
                                            st.dataframe(output_df[available_preview_cols].head(5), use_container_width=True)
                                        
                                        # Process button
                                        if st.button("Process DNC Cleaning", key="dnc_process_btn"):
                                            with st.spinner("Processing DNC phone number cleaning..."):
                                                progress_bar.progress(0.2)
                                                
                                                if not available_pairs:
                                                    st.error("No phone/DNC pairs to process.")
                                                else:
                                                    processing_text.text("Removing phone numbers where DNC = 'Y'...")
                                                    progress_bar.progress(0.4)
                                                    
                                                    # Count original phone numbers
                                                    original_phones = {}
                                                    for phone_col, _ in available_pairs:
                                                        original_phones[phone_col] = sum(output_df[phone_col].notna() & (output_df[phone_col] != ''))
                                                    
                                                    # Clean and prepare all DNC columns - normalize to uppercase
                                                    for _, dnc_col in available_pairs:
                                                        output_df[dnc_col] = output_df[dnc_col].fillna('N').astype(str).str.strip().str.upper()
                                                    
                                                    # Clean phone columns - normalize empty values
                                                    for phone_col, _ in available_pairs:
                                                        output_df[phone_col] = output_df[phone_col].fillna('').astype(str)
                                                        output_df[phone_col] = output_df[phone_col].apply(
                                                            lambda x: '' if str(x).upper() in ['NAN', 'NONE', 'NULL', ''] else str(x).strip()
                                                        )
                                                    
                                                    progress_bar.progress(0.6)
                                                    
                                                    # Track rows that had phone numbers removed due to DNC 'Y'
                                                    rows_with_dnc_y = set()
                                                    rows_processed_count = 0
                                                    phones_cleared = 0
                                                    
                                                    # Process each row individually to handle complex patterns
                                                    for idx in range(len(output_df)):
                                                        # Process each phone/DNC pair independently
                                                        for phone_col, dnc_col in available_pairs:
                                                            dnc_value = output_df.at[idx, dnc_col]
                                                            phone_value = output_df.at[idx, phone_col]
                                                            
                                                            # Skip if DNC is empty or N
                                                            if not dnc_value or dnc_value == 'N':
                                                                continue
                                                            
                                                            # Skip if phone is already empty
                                                            if not phone_value or phone_value == '':
                                                                continue
                                                            
                                                            rows_processed_count += 1
                                                            
                                                            # Case 1: Simple DNC 'Y' - remove entire phone field
                                                            if dnc_value in ['Y', 'YES', 'TRUE', '1']:
                                                                output_df.at[idx, phone_col] = ''
                                                                rows_with_dnc_y.add(idx)
                                                                phones_cleared += 1
                                                            
                                                            # Case 2: Comma-separated DNC values - match positionally with phone numbers
                                                            elif ',' in dnc_value:
                                                                dnc_list = [d.strip() for d in dnc_value.split(',') if d.strip()]
                                                                
                                                                # If phone also has commas, match positionally
                                                                if ',' in phone_value:
                                                                    phone_list = [p.strip() for p in phone_value.split(',') if p.strip()]
                                                                    
                                                                    # Keep only phones where corresponding DNC is not 'Y'
                                                                    kept_phones = []
                                                                    had_removal = False
                                                                    
                                                                    for i in range(len(phone_list)):
                                                                        # Use corresponding DNC value, or 'N' if no corresponding value exists
                                                                        dnc_for_phone = dnc_list[i] if i < len(dnc_list) else 'N'
                                                                        
                                                                        if dnc_for_phone not in ['Y', 'YES', 'TRUE', '1']:
                                                                            kept_phones.append(phone_list[i])
                                                                        else:
                                                                            had_removal = True
                                                                    
                                                                    # Update the phone field
                                                                    output_df.at[idx, phone_col] = ', '.join(kept_phones) if kept_phones else ''
                                                                    if had_removal:
                                                                        rows_with_dnc_y.add(idx)
                                                                        phones_cleared += 1
                                                                
                                                                else:
                                                                    # Single phone with comma-separated DNC
                                                                    # Use the FIRST DNC value to decide
                                                                    first_dnc = dnc_list[0] if dnc_list else 'N'
                                                                    if first_dnc in ['Y', 'YES', 'TRUE', '1']:
                                                                        output_df.at[idx, phone_col] = ''
                                                                        rows_with_dnc_y.add(idx)
                                                                        phones_cleared += 1
                                                    
                                                    # Debug info
                                                    st.info(f"🔍 **Debug:** Processed {rows_processed_count} phone/DNC checks, cleared {phones_cleared} phone fields")
                                                
                                                    progress_bar.progress(0.8)
                                                    
                                                    # Calculate statistics
                                                    final_phones = {}
                                                    phones_removed = {}
                                                    for phone_col, _ in available_pairs:
                                                        final_phones[phone_col] = sum(output_df[phone_col].notna() & (output_df[phone_col] != ''))
                                                        phones_removed[phone_col] = original_phones[phone_col] - final_phones[phone_col]
                                                    
                                                    total_phones_removed = sum(phones_removed.values())
                                                    dnc_y_count = len(rows_with_dnc_y)
                                                    dnc_n_count = len(output_df) - dnc_y_count
                                                
                                                    progress_bar.progress(1.0)
                                                    
                                                    # Display results
                                                    st.success(f"✅ DNC phone number cleaning complete! Processed {len(output_df):,} rows")
                                                
                                                    # Show detailed statistics
                                                    st.subheader("Cleaning Statistics")
                                                    
                                                    # Summary metrics
                                                    col1, col2, col3, col4 = st.columns(4)
                                                    with col1:
                                                        st.metric("Total Rows", f"{len(output_df):,}")
                                                    with col2:
                                                        st.metric("DNC 'Y' Records", f"{dnc_y_count:,}")
                                                    with col3:
                                                        st.metric("DNC 'N' Records", f"{dnc_n_count:,}")
                                                    with col4:
                                                        st.metric("Phones Removed", f"{total_phones_removed:,}")
                                                
                                                    # Detailed phone number statistics
                                                    if available_pairs:
                                                        with st.expander("Detailed Phone Number Statistics"):
                                                            phone_stats = []
                                                            for phone_col, dnc_col in available_pairs:
                                                                phone_stats.append({
                                                                    'Phone Column': phone_col,
                                                                    'DNC Column': dnc_col,
                                                                    'Original Count': original_phones[phone_col],
                                                                    'Final Count': final_phones[phone_col],
                                                                    'Removed': phones_removed[phone_col],
                                                                    'Removal %': f"{(phones_removed[phone_col] / original_phones[phone_col] * 100) if original_phones[phone_col] > 0 else 0:.1f}%"
                                                                })
                                                            
                                                            stats_df = pd.DataFrame(phone_stats)
                                                            st.dataframe(stats_df, use_container_width=True)
                                                    
                                                    # Show sample of cleaned data
                                                    with st.expander("Sample of Processed Data"):
                                                        sample_cols = []
                                                        for phone_col, dnc_col in available_pairs:
                                                            sample_cols.extend([phone_col, dnc_col])
                                                        if 'FIRST_NAME' in output_df.columns:
                                                            sample_cols = ['FIRST_NAME', 'LAST_NAME'] + sample_cols
                                                    
                                                        # Show samples of both Y and N records
                                                        # Find rows where any DNC column contains 'Y'
                                                        has_y_mask = pd.Series([False] * len(output_df))
                                                        for _, dnc_col in available_pairs:
                                                            has_y_mask |= output_df[dnc_col].str.contains('Y', na=False, regex=False)
                                                        
                                                        dnc_y_sample = output_df[has_y_mask].head(5)
                                                        dnc_n_sample = output_df[~has_y_mask].head(5)
                                                        
                                                        if not dnc_y_sample.empty:
                                                            st.write("**Sample DNC 'Y' records (corresponding phone numbers should be empty):**")
                                                            available_sample_cols = [col for col in sample_cols if col in output_df.columns]
                                                            st.dataframe(dnc_y_sample[available_sample_cols], use_container_width=True)
                                                        
                                                        if not dnc_n_sample.empty:
                                                            st.write("**Sample DNC 'N' records (phone numbers should be preserved):**")
                                                            available_sample_cols = [col for col in sample_cols if col in output_df.columns]
                                                            st.dataframe(dnc_n_sample[available_sample_cols], use_container_width=True)
                                                    
                                                    # Show processing summary
                                                    phone_col_names = [phone_col for phone_col, _ in available_pairs]
                                                    dnc_col_names = [dnc_col for _, dnc_col in available_pairs]
                                                    st.info(f"""
                                                    **Processing Summary:**
                                                    - 📋 Processed {len(available_pairs)} phone/DNC column pairs
                                                    - 📞 Phone columns: {', '.join(phone_col_names)}
                                                    - 🚫 DNC columns: {', '.join(dnc_col_names)}
                                                    - 🚫 Removed phone numbers from {dnc_y_count:,} records with DNC 'Y' ({dnc_y_count/len(output_df)*100:.1f}%)
                                                    - ✅ Preserved phone numbers in {dnc_n_count:,} records ({dnc_n_count/len(output_df)*100:.1f}%)
                                                    - 📱 Total phone numbers removed: {total_phones_removed:,}
                                                    """)
                                                    
                                                    # Verification: Check that no records have phone numbers when their DNC column contains 'Y'
                                                    verification_issues = []
                                                    problematic_rows = []
                                                    
                                                    for phone_col, dnc_col in available_pairs:
                                                        # Find rows where DNC contains 'Y' but phone is not empty
                                                        mask = (output_df[dnc_col].str.contains('Y', na=False, regex=False)) & \
                                                               (output_df[phone_col].notna()) & \
                                                               (output_df[phone_col] != '')
                                                        
                                                        dnc_y_with_phones = mask.sum()
                                                        
                                                        if dnc_y_with_phones > 0:
                                                            verification_issues.append(f"{phone_col}/{dnc_col}: {dnc_y_with_phones} records")
                                                            
                                                            # Collect problematic rows for debugging
                                                            problem_indices = output_df[mask].index.tolist()[:10]  # First 10
                                                            for idx in problem_indices:
                                                                problematic_rows.append({
                                                                    'Row': idx + 2,  # +2 for Excel (header + 0-index)
                                                                    'Phone Column': phone_col,
                                                                    'Phone Value': output_df.at[idx, phone_col],
                                                                    'DNC Column': dnc_col,
                                                                    'DNC Value': output_df.at[idx, dnc_col]
                                                                })
                                                    
                                                    if verification_issues:
                                                        st.error("❌ **Verification Failed:**\n- " + "\n- ".join(verification_issues))
                                                        
                                                        # Show problematic rows for debugging
                                                        with st.expander("🔍 Debug: Problematic Rows (first 10)"):
                                                            st.warning("These rows have DNC='Y' but still have phone numbers:")
                                                            debug_df = pd.DataFrame(problematic_rows)
                                                            st.dataframe(debug_df, use_container_width=True)
                                                            
                                                            st.info("""
                                                            **Debug Information:**
                                                            - Row numbers shown are Excel row numbers (with header)
                                                            - DNC values should be 'Y' or contain 'Y'
                                                            - Phone values should be empty but are not
                                                            - This suggests the cleaning logic didn't process these rows
                                                            """)
                                                    else:
                                                        st.success("✅ **Verification Passed:** All phone numbers with DNC containing 'Y' have been removed successfully!")
                                                
                                                    # Provide download options
                                                    output_format = st.radio("Output format:", 
                                                                           ("CSV", "Excel", "JSON"), 
                                                                           horizontal=True,
                                                                           key="dnc_output_format")
                                                    
                                                    create_download_button(
                                                        output_df,
                                                        "dnc_cleaned_simple",
                                                        output_format.lower(),
                                                        f"Download DNC cleaned data with {len(output_df):,} rows"
                                                    )
                                
                                # ADDRESS + HONWINCOME (basic version without names)
                                elif option == "Address + HoNWIncome":
                                        processing_text.text("Processing addresses with homeowner, net worth, and income data...")
                                        
                                        # Clean addresses if requested
                                        if st.session_state['user_preferences']['auto_clean_addresses']:
                                            df = df[df['PERSONAL_ADDRESS'].notna()]
                                            df['PERSONAL_ADDRESS_CLEAN'] = df['PERSONAL_ADDRESS'].apply(clean_address)
                                            progress_bar.progress(0.2)
                                        
                                        # Create the address components
                                        address_components = ['PERSONAL_ADDRESS_CLEAN'] if 'PERSONAL_ADDRESS_CLEAN' in df.columns else ['PERSONAL_ADDRESS']
                                        if 'PERSONAL_CITY' in df.columns:
                                            address_components.append('PERSONAL_CITY')
                                        if 'PERSONAL_STATE' in df.columns:
                                            address_components.append('PERSONAL_STATE')
                                        
                                        # Create the address field
                                        df['ADDRESS'] = df[address_components].apply(
                                            lambda row: ', '.join([str(x) for x in row if pd.notna(x) and x != '']), axis=1
                                        )
                                        
                                        # Handle missing values for HoNWIncome data
                                        df['HOMEOWNER'] = df['HOMEOWNER'].fillna('') if 'HOMEOWNER' in df.columns else ''
                                        df['NET_WORTH'] = df['NET_WORTH'].fillna('') if 'NET_WORTH' in df.columns else ''
                                        df['INCOME_RANGE'] = df['INCOME_RANGE'].fillna('') if 'INCOME_RANGE' in df.columns else ''
                                        
                                        # Create the data field with HoNWIncome information
                                        honw_parts = []
                                        if 'HOMEOWNER' in df.columns:
                                            honw_parts.append('Ho ' + df['HOMEOWNER'].astype(str))
                                        if 'NET_WORTH' in df.columns:
                                            honw_parts.append('NW ' + df['NET_WORTH'].astype(str))
                                        if 'INCOME_RANGE' in df.columns:
                                            honw_parts.append('Income ' + df['INCOME_RANGE'].astype(str))
                                        
                                        if honw_parts:
                                            # Combine the Series objects using string concatenation
                                            df['DATA'] = honw_parts[0]
                                            for part in honw_parts[1:]:
                                                df['DATA'] = df['DATA'] + ' | ' + part
                                        else:
                                            df['DATA'] = 'No HoNWIncome data available'
                                        
                                        # Create output with address and data only
                                        output_df = df[['ADDRESS', 'DATA']].copy()
                                        
                                        progress_bar.progress(0.6)
                                        
                                        st.success(f"✅ Processing complete! Generated {len(output_df):,} rows with address and HoNWIncome data")
                                        
                                        # Show data summary
                                        complete_records = sum(
                                            output_df['ADDRESS'].notna() & 
                                            (output_df['ADDRESS'] != '')
                                        )
                                        st.write(f"**Complete records (with address):** {complete_records:,} ({complete_records/len(output_df)*100:.1f}%)")
                                        
                                        # Provide download options
                                        output_format = st.radio("Output format:", 
                                                               ("CSV", "Excel", "JSON"), 
                                                               horizontal=True)
                                        
                                        create_download_button(
                                            output_df,
                                            "address_honwincome",
                                            output_format.lower(),
                                            f"Download {len(output_df):,} records with address and HoNWIncome data"
                                        )
                                        
                                        # Add Google My Maps instructions
                                        with st.expander("How to Import into Google My Maps"):
                                            st.markdown("""
                                            ### How to Import into Google My Maps:
                                            1. Go to [Google My Maps](https://www.google.com/mymaps).
                                            2. Click **Create a new map**.
                                            3. In the new map, click **Import** under the layer section.
                                            4. Upload the downloaded CSV file(s) or extract from ZIP.
                                            5. Set the following:
                                               - **Placemarker Pins**: Select the `ADDRESS` column.
                                               - **Placemarker Name (Title)**: Select the `DATA` column.
                                            6. Dismiss any locations that result in an error during import.
                                            7. Zoom out and manually delete any pins that are significantly distant from the main cluster.
                                            """)
                                        
                                        progress_bar.progress(1.0)
                                
                                # ADDRESS + HONWINCOME & PHONE (basic version without names)
                                elif option == "Address + HoNWIncome & Phone":
                                        processing_text.text("Processing addresses with homeowner, net worth, income, and phone data...")
                                        
                                        # Clean addresses if requested
                                        if st.session_state['user_preferences']['auto_clean_addresses']:
                                            df = df[df['PERSONAL_ADDRESS'].notna()]
                                            df['PERSONAL_ADDRESS_CLEAN'] = df['PERSONAL_ADDRESS'].apply(clean_address)
                                            progress_bar.progress(0.2)
                                        
                                        # Create the address field
                                        address_components = ['PERSONAL_ADDRESS_CLEAN'] if 'PERSONAL_ADDRESS_CLEAN' in df.columns else ['PERSONAL_ADDRESS']
                                        if 'PERSONAL_CITY' in df.columns:
                                            address_components.append('PERSONAL_CITY')
                                        if 'PERSONAL_STATE' in df.columns:
                                            address_components.append('PERSONAL_STATE')
                                        
                                        df['ADDRESS'] = df[address_components].apply(
                                            lambda row: ', '.join([str(x) for x in row if pd.notna(x) and x != '']), axis=1
                                        )
                                        
                                        # Handle missing values
                                        df['MOBILE_PHONE'] = df['MOBILE_PHONE'].fillna('')
                                        df['DNC'] = df['DNC'].fillna('N')
                                        df['HOMEOWNER'] = df['HOMEOWNER'].fillna('') if 'HOMEOWNER' in df.columns else ''
                                        df['NET_WORTH'] = df['NET_WORTH'].fillna('') if 'NET_WORTH' in df.columns else ''
                                        df['INCOME_RANGE'] = df['INCOME_RANGE'].fillna('') if 'INCOME_RANGE' in df.columns else ''
                                        
                                        # Format phone numbers if needed
                                        if st.session_state['user_preferences'].get('format_phone_numbers', True):
                                            df['MOBILE_PHONE'] = df['MOBILE_PHONE'].apply(validate_phone)
                                        
                                        # Create the data field with HoNWIncome and phone info
                                        honw_parts = []
                                        if 'HOMEOWNER' in df.columns:
                                            honw_parts.append('Ho ' + df['HOMEOWNER'].astype(str))
                                        if 'NET_WORTH' in df.columns:
                                            honw_parts.append('NW ' + df['NET_WORTH'].astype(str))
                                        if 'INCOME_RANGE' in df.columns:
                                            honw_parts.append('Income ' + df['INCOME_RANGE'].astype(str))
                                        
                                        # Create base data field
                                        if honw_parts:
                                            # Combine the Series objects using string concatenation
                                            df['DATA'] = honw_parts[0]
                                            for part in honw_parts[1:]:
                                                df['DATA'] = df['DATA'] + ' | ' + part
                                        else:
                                            df['DATA'] = 'No HoNWIncome data'
                                        
                                        # Add phone for non-DNC records
                                        df['DATA'] = df['DATA'] + \
                                                df.apply(lambda row: ' | Phone ' + str(row['MOBILE_PHONE']) if (
                                                        row['DNC'] != 'Y' and row['MOBILE_PHONE'] != '') else '', axis=1)
                                        
                                        # Create output
                                        output_df = df[['ADDRESS', 'DATA']].copy()
                                        
                                        progress_bar.progress(0.6)
                                        
                                        st.success(f"✅ Processing complete! Generated {len(output_df):,} rows with address, HoNWIncome, and phone data")
                                        
                                        # Add stats about phone numbers
                                        total_phones = len(df[df['MOBILE_PHONE'] != ''])
                                        callable_phones = len(df[(df['MOBILE_PHONE'] != '') & (df['DNC'] != 'Y')])
                                        
                                        st.write(f"**Total records with phone numbers:** {total_phones:,} ({total_phones/len(df)*100:.1f}%)")
                                        st.write(f"**Callable phone numbers (not DNC):** {callable_phones:,} ({callable_phones/len(df)*100:.1f}%)")
                                        
                                        # Provide download options
                                        output_format = st.radio("Output format:", 
                                                               ("CSV", "Excel", "JSON"), 
                                                               horizontal=True)
                                        
                                        create_download_button(
                                            output_df,
                                            "address_honwincome_phone",
                                            output_format.lower(),
                                            f"Download {len(output_df):,} records with address, HoNWIncome, and phone data"
                                        )
                                        
                                        # Add Google My Maps instructions
                                        with st.expander("How to Import into Google My Maps"):
                                            st.markdown("""
                                            ### How to Import into Google My Maps:
                                            1. Go to [Google My Maps](https://www.google.com/mymaps).
                                            2. Click **Create a new map**.
                                            3. In the new map, click **Import** under the layer section.
                                            4. Upload the downloaded CSV file(s) or extract from ZIP.
                                            5. Set the following:
                                               - **Placemarker Pins**: Select the `ADDRESS` column.
                                               - **Placemarker Name (Title)**: Select the `DATA` column.
                                            6. Dismiss any locations that result in an error during import.
                                            7. Zoom out and manually delete any pins that are significantly distant from the main cluster.
                                            """)
                                        
                                        progress_bar.progress(1.0)
                                
                                # FULL COMBINED ADDRESS
                                elif option == "Full Combined Address":
                                        processing_text.text("Processing comprehensive address data with metadata...")
                                        
                                        # Clean addresses if requested
                                        if st.session_state['user_preferences']['auto_clean_addresses']:
                                            df = df[df['PERSONAL_ADDRESS'].notna()]
                                            df['PERSONAL_ADDRESS_CLEAN'] = df['PERSONAL_ADDRESS'].apply(clean_address)
                                            progress_bar.progress(0.2)
                                        
                                        # Create comprehensive output columns
                                        output_columns = ['FIRST_NAME', 'LAST_NAME']
                                        
                                        # Add cleaned or original address
                                        if 'PERSONAL_ADDRESS_CLEAN' in df.columns:
                                            output_columns.append('PERSONAL_ADDRESS_CLEAN')
                                        else:
                                            output_columns.append('PERSONAL_ADDRESS')
                                        
                                        # Add address components
                                        address_cols = ['PERSONAL_CITY', 'PERSONAL_STATE', 'PERSONAL_ZIP', 'PERSONAL_ZIP4']
                                        for col in address_cols:
                                            if col in df.columns:
                                                output_columns.append(col)
                                        
                                        # Add phone numbers
                                        phone_cols = ['MOBILE_PHONE', 'DIRECT_NUMBER', 'PERSONAL_PHONE']
                                        for col in phone_cols:
                                            if col in df.columns:
                                                output_columns.append(col)
                                        
                                        # Add demographic data
                                        demo_cols = ['AGE_RANGE', 'GENDER', 'HOMEOWNER', 'NET_WORTH', 'INCOME_RANGE', 'MARRIED', 'CHILDREN']
                                        for col in demo_cols:
                                            if col in df.columns:
                                                output_columns.append(col)
                                        
                                        # Add email columns
                                        email_cols = ['PERSONAL_EMAILS', 'BUSINESS_EMAIL']
                                        for col in email_cols:
                                            if col in df.columns:
                                                output_columns.append(col)
                                        
                                        # Create output with available columns
                                        available_columns = [col for col in output_columns if col in df.columns]
                                        output_df = df[available_columns].copy()
                                        
                                        # Format phone numbers if enabled
                                        if st.session_state['user_preferences'].get('format_phone_numbers', True):
                                            for col in phone_cols:
                                                if col in output_df.columns:
                                                    output_df[col] = output_df[col].apply(validate_phone)
                                        
                                        progress_bar.progress(0.6)
                                        
                                        st.success(f"✅ Processing complete! Generated comprehensive dataset with {len(output_df):,} rows and {len(output_df.columns):,} columns")
                                        
                                        # Show data summary
                                        complete_records = sum(
                                            output_df['FIRST_NAME'].notna() & 
                                            output_df['LAST_NAME'].notna() & 
                                            output_df[available_columns[2]].notna()  # Address column
                                        )
                                        st.write(f"**Complete records (with name and address):** {complete_records:,} ({complete_records/len(output_df)*100:.1f}%)")
                                        
                                        # Show columns included
                                        with st.expander("Columns Included in Full Combined Address"):
                                            col_categories = {
                                                "Identity": ['FIRST_NAME', 'LAST_NAME'],
                                                "Address": ['PERSONAL_ADDRESS_CLEAN', 'PERSONAL_ADDRESS', 'PERSONAL_CITY', 'PERSONAL_STATE', 'PERSONAL_ZIP', 'PERSONAL_ZIP4'],
                                                "Phone Numbers": ['MOBILE_PHONE', 'DIRECT_NUMBER', 'PERSONAL_PHONE'],
                                                "Demographics": ['AGE_RANGE', 'GENDER', 'HOMEOWNER', 'NET_WORTH', 'INCOME_RANGE', 'MARRIED', 'CHILDREN'],
                                                "Email": ['PERSONAL_EMAILS', 'BUSINESS_EMAIL']
                                            }
                                            
                                            for category, cols in col_categories.items():
                                                included_cols = [col for col in cols if col in available_columns]
                                                if included_cols:
                                                    st.write(f"**{category}:** {', '.join(included_cols)}")
                                        
                                        # Provide download options
                                        output_format = st.radio("Output format:", 
                                                               ("CSV", "Excel", "JSON"), 
                                                               horizontal=True)
                                        
                                        create_download_button(
                                            output_df,
                                            "full_combined_address",
                                            output_format.lower(),
                                            f"Download comprehensive dataset with {len(output_df):,} rows"
                                        )
                                        
                                        progress_bar.progress(1.0)
                                
                                # PHONE & CREDIT SCORE
                                elif option == "Phone & Credit Score":
                                        processing_text.text("Processing phone numbers and credit scores with address details...")
                                        
                                        # Clean addresses if requested
                                        if st.session_state['user_preferences']['auto_clean_addresses']:
                                            df = df[df['PERSONAL_ADDRESS'].notna()]
                                            df['PERSONAL_ADDRESS_CLEAN'] = df['PERSONAL_ADDRESS'].apply(clean_address)
                                            progress_bar.progress(0.2)
                                        
                                        # Select relevant columns for phone & credit focus
                                        output_columns = ['FIRST_NAME', 'LAST_NAME']
                                        
                                        # Add address columns
                                        if 'PERSONAL_ADDRESS_CLEAN' in df.columns:
                                            output_columns.append('PERSONAL_ADDRESS_CLEAN')
                                        else:
                                            output_columns.append('PERSONAL_ADDRESS')
                                        
                                        address_cols = ['PERSONAL_CITY', 'PERSONAL_STATE', 'PERSONAL_ZIP']
                                        for col in address_cols:
                                            if col in df.columns:
                                                output_columns.append(col)
                                        
                                        # Add all available phone columns
                                        phone_cols = ['MOBILE_PHONE', 'DIRECT_NUMBER', 'PERSONAL_PHONE']
                                        for col in phone_cols:
                                            if col in df.columns:
                                                output_columns.append(col)
                                        
                                        # Add credit score and related columns
                                        credit_cols = ['SKIPTRACE_CREDIT_RATING']
                                        for col in credit_cols:
                                            if col in df.columns:
                                                output_columns.append(col)
                                        
                                        # Add DNC status
                                        if 'DNC' in df.columns:
                                            output_columns.append('DNC')
                                        
                                        # Create output with available columns
                                        available_columns = [col for col in output_columns if col in df.columns]
                                        output_df = df[available_columns].copy()
                                        
                                        # Format phone numbers if enabled
                                        if st.session_state['user_preferences'].get('format_phone_numbers', True):
                                            for col in phone_cols:
                                                if col in output_df.columns:
                                                    output_df[col] = output_df[col].apply(validate_phone)
                                        
                                        progress_bar.progress(0.6)
                                        
                                        st.success(f"✅ Processing complete! Generated {len(output_df):,} rows focused on phone numbers and credit scores")
                                        
                                        # Show statistics
                                        available_phone_cols = [col for col in phone_cols if col in output_df.columns]
                                        phone_stats = {}
                                        for col in available_phone_cols:
                                            phone_stats[col] = sum(output_df[col].notna() & (output_df[col] != ''))
                                        
                                        if phone_stats:
                                            st.write("**Phone Number Statistics:**")
                                            for col, count in phone_stats.items():
                                                st.write(f"- **{col}:** {count:,} records ({count/len(output_df)*100:.1f}%)")
                                        
                                        # Credit score statistics
                                        if 'SKIPTRACE_CREDIT_RATING' in output_df.columns:
                                            credit_records = sum(output_df['SKIPTRACE_CREDIT_RATING'].notna() & (output_df['SKIPTRACE_CREDIT_RATING'] != ''))
                                            st.write(f"**Credit Scores Available:** {credit_records:,} records ({credit_records/len(output_df)*100:.1f}%)")
                                        
                                        # DNC statistics
                                        if 'DNC' in output_df.columns:
                                            dnc_y = sum(output_df['DNC'] == 'Y')
                                            dnc_n = sum(output_df['DNC'] == 'N')
                                            st.write(f"**DNC Status:** {dnc_y:,} DNC 'Y', {dnc_n:,} DNC 'N'")
                                        
                                        # Provide download options
                                        output_format = st.radio("Output format:", 
                                                               ("CSV", "Excel", "JSON"), 
                                                               horizontal=True)
                                        
                                        create_download_button(
                                            output_df,
                                            "phone_credit_score",
                                            output_format.lower(),
                                            f"Download {len(output_df):,} records with phone and credit data"
                                        )
                                        
                                        progress_bar.progress(1.0)
                                
                                # COMPLETE CONTACT EXPORT
                                elif option == "Complete Contact Export":
                                        processing_text.text("Processing and cleaning complete contact dataset...")
                                        
                                        # Make a copy to preserve original structure
                                        output_df = df.copy()
                                        
                                        # Clean addresses if they exist and auto-clean is enabled
                                        if 'PERSONAL_ADDRESS' in output_df.columns and st.session_state['user_preferences']['auto_clean_addresses']:
                                            processing_text.text("Cleaning personal addresses...")
                                            # Only clean addresses that exist
                                            mask = output_df['PERSONAL_ADDRESS'].notna()
                                            output_df.loc[mask, 'PERSONAL_ADDRESS'] = output_df.loc[mask, 'PERSONAL_ADDRESS'].apply(clean_address)
                                            progress_bar.progress(0.2)
                                        
                                        # Clean business addresses if they exist
                                        if 'COMPANY_ADDRESS' in output_df.columns and st.session_state['user_preferences']['auto_clean_addresses']:
                                            processing_text.text("Cleaning business addresses...")
                                            mask = output_df['COMPANY_ADDRESS'].notna()
                                            output_df.loc[mask, 'COMPANY_ADDRESS'] = output_df.loc[mask, 'COMPANY_ADDRESS'].apply(clean_address)
                                            progress_bar.progress(0.4)
                                        
                                        # Format phone numbers if enabled
                                        phone_cols = ['MOBILE_PHONE', 'DIRECT_NUMBER', 'PERSONAL_PHONE', 'COMPANY_PHONE']
                                        available_phone_cols = [col for col in phone_cols if col in output_df.columns]
                                        
                                        if available_phone_cols and st.session_state['user_preferences'].get('format_phone_numbers', True):
                                            processing_text.text("Formatting phone numbers...")
                                            for col in available_phone_cols:
                                                output_df[col] = output_df[col].apply(validate_phone)
                                            progress_bar.progress(0.6)
                                        
                                        progress_bar.progress(0.8)
                                        
                                        st.success(f"✅ Complete contact export ready! Processed {len(output_df):,} rows with {len(output_df.columns):,} columns")
                                        
                                        # Show comprehensive statistics
                                        st.subheader("Dataset Overview")
                                        
                                        # Basic statistics
                                        col1, col2, col3, col4 = st.columns(4)
                                        with col1:
                                            st.metric("Total Records", f"{len(output_df):,}")
                                        with col2:
                                            st.metric("Total Columns", f"{len(output_df.columns):,}")
                                        with col3:
                                            complete_names = sum(output_df['FIRST_NAME'].notna() & output_df['LAST_NAME'].notna()) if 'FIRST_NAME' in output_df.columns and 'LAST_NAME' in output_df.columns else 0
                                            st.metric("Complete Names", f"{complete_names:,}")
                                        with col4:
                                            complete_addresses = sum(output_df['PERSONAL_ADDRESS'].notna()) if 'PERSONAL_ADDRESS' in output_df.columns else 0
                                            st.metric("Personal Addresses", f"{complete_addresses:,}")
                                        
                                        # Show data quality metrics
                                        with st.expander("Data Quality Metrics"):
                                            quality_metrics = []
                                            
                                            # Contact information completeness
                                            if available_phone_cols:
                                                for col in available_phone_cols:
                                                    non_empty = sum(output_df[col].notna() & (output_df[col] != ''))
                                                    quality_metrics.append({
                                                        'Field': col,
                                                        'Non-Empty Records': non_empty,
                                                        'Completeness %': f"{non_empty/len(output_df)*100:.1f}%"
                                                    })
                                            
                                            # Email completeness
                                            email_cols = ['PERSONAL_EMAILS', 'BUSINESS_EMAIL']
                                            for col in email_cols:
                                                if col in output_df.columns:
                                                    non_empty = sum(output_df[col].notna() & (output_df[col] != ''))
                                                    quality_metrics.append({
                                                        'Field': col,
                                                        'Non-Empty Records': non_empty,
                                                        'Completeness %': f"{non_empty/len(output_df)*100:.1f}%"
                                                    })
                                            
                                            if quality_metrics:
                                                quality_df = pd.DataFrame(quality_metrics)
                                                st.dataframe(quality_df, use_container_width=True)
                                        
                                        # Show column categories
                                        with st.expander("Complete Column List by Category"):
                                            col_categories = {
                                                "Identity": [col for col in output_df.columns if col in ['FIRST_NAME', 'LAST_NAME', 'UUID']],
                                                "Personal Address": [col for col in output_df.columns if 'PERSONAL_' in col and any(addr in col for addr in ['ADDRESS', 'CITY', 'STATE', 'ZIP'])],
                                                "Phone Numbers": [col for col in output_df.columns if 'PHONE' in col or col in ['MOBILE_PHONE', 'DIRECT_NUMBER']],
                                                "Email": [col for col in output_df.columns if 'EMAIL' in col],
                                                "Business/Professional": [col for col in output_df.columns if any(prefix in col for prefix in ['COMPANY_', 'PROFESSIONAL_', 'JOB_', 'BUSINESS_'])],
                                                "Demographics": [col for col in output_df.columns if col in ['AGE_RANGE', 'GENDER', 'HOMEOWNER', 'NET_WORTH', 'INCOME_RANGE', 'MARRIED', 'CHILDREN']],
                                                "Skiptrace Data": [col for col in output_df.columns if 'SKIPTRACE_' in col],
                                                "Other": []
                                            }
                                            
                                            # Assign uncategorized columns to "Other"
                                            categorized_cols = []
                                            for category_cols in col_categories.values():
                                                categorized_cols.extend(category_cols)
                                            col_categories["Other"] = [col for col in output_df.columns if col not in categorized_cols]
                                            
                                            for category, cols in col_categories.items():
                                                if cols:
                                                    st.write(f"**{category} ({len(cols)} columns):** {', '.join(cols)}")
                                        
                                        # Show sample data
                                        if st.session_state['user_preferences']['show_preview']:
                                            with st.expander("Sample Data Preview"):
                                                sample_cols = []
                                                if 'FIRST_NAME' in output_df.columns:
                                                    sample_cols.extend(['FIRST_NAME', 'LAST_NAME'])
                                                if 'PERSONAL_ADDRESS' in output_df.columns:
                                                    sample_cols.append('PERSONAL_ADDRESS')
                                                if available_phone_cols:
                                                    sample_cols.append(available_phone_cols[0])  # Add first phone column
                                                
                                                if sample_cols:
                                                    st.dataframe(output_df[sample_cols].head(10), use_container_width=True)
                                        
                                        # Provide download options
                                        output_format = st.radio("Output format:", 
                                                               ("CSV", "Excel", "JSON"), 
                                                               horizontal=True)
                                        
                                        create_download_button(
                                            output_df,
                                            "complete_contact_export",
                                            output_format.lower(),
                                            f"Download complete cleaned dataset with {len(output_df):,} rows"
                                        )
                                        
                                        progress_bar.progress(1.0)
                                
                                # ADDRESS + HONWINCOME FIRST NAME LAST NAME
                                elif option == "Address + HoNWIncome First Name Last Name":
                                        processing_text.text("Processing addresses with homeowner, net worth, income data, and names...")
                                        
                                        # Clean addresses if requested
                                        if st.session_state['user_preferences']['auto_clean_addresses']:
                                            df = df[df['PERSONAL_ADDRESS'].notna()]
                                            df['PERSONAL_ADDRESS_CLEAN'] = df['PERSONAL_ADDRESS'].apply(clean_address)
                                            progress_bar.progress(0.2)
                                        
                                        # Create the address components
                                        address_components = ['PERSONAL_ADDRESS_CLEAN'] if 'PERSONAL_ADDRESS_CLEAN' in df.columns else ['PERSONAL_ADDRESS']
                                        if 'PERSONAL_CITY' in df.columns:
                                            address_components.append('PERSONAL_CITY')
                                        if 'PERSONAL_STATE' in df.columns:
                                            address_components.append('PERSONAL_STATE')
                                        
                                        # Create the address field
                                        df['ADDRESS'] = df[address_components].apply(
                                            lambda row: ', '.join([str(x) for x in row if pd.notna(x) and x != '']), axis=1
                                        )
                                        
                                        # Handle missing values for HoNWIncome data
                                        df['HOMEOWNER'] = df['HOMEOWNER'].fillna('') if 'HOMEOWNER' in df.columns else ''
                                        df['NET_WORTH'] = df['NET_WORTH'].fillna('') if 'NET_WORTH' in df.columns else ''
                                        df['INCOME_RANGE'] = df['INCOME_RANGE'].fillna('') if 'INCOME_RANGE' in df.columns else ''
                                        
                                        # Create the data field with HoNWIncome information
                                        honw_parts = []
                                        if 'HOMEOWNER' in df.columns:
                                            honw_parts.append('Ho ' + df['HOMEOWNER'].astype(str))
                                        if 'NET_WORTH' in df.columns:
                                            honw_parts.append('NW ' + df['NET_WORTH'].astype(str))
                                        if 'INCOME_RANGE' in df.columns:
                                            honw_parts.append('Income ' + df['INCOME_RANGE'].astype(str))
                                        
                                        if honw_parts:
                                            # Combine the Series objects using string concatenation
                                            df['DATA'] = honw_parts[0]
                                            for part in honw_parts[1:]:
                                                df['DATA'] = df['DATA'] + ' | ' + part
                                        else:
                                            df['DATA'] = 'No HoNWIncome data available'
                                        
                                        # Create output with names and address data
                                        output_df = df[['FIRST_NAME', 'LAST_NAME', 'ADDRESS', 'DATA']].copy()
                                        
                                        progress_bar.progress(0.6)
                                        
                                        st.success(f"✅ Processing complete! Generated {len(output_df):,} rows with names and address data")
                                        
                                        # Show data summary
                                        complete_records = sum(
                                            output_df['FIRST_NAME'].notna() & 
                                            output_df['LAST_NAME'].notna() & 
                                            output_df['ADDRESS'].notna() & 
                                            (output_df['ADDRESS'] != '')
                                        )
                                        st.write(f"**Complete records (with name and address):** {complete_records:,} ({complete_records/len(output_df)*100:.1f}%)")
                                        
                                        # Provide download options
                                        output_format = st.radio("Output format:", 
                                                               ("CSV", "Excel", "JSON"), 
                                                               horizontal=True)
                                        
                                        create_download_button(
                                            output_df,
                                            "address_honwincome_names",
                                            output_format.lower(),
                                            f"Download {len(output_df):,} records with names and address data"
                                        )
                                        
                                        # Add Google My Maps instructions
                                        with st.expander("How to Import into Google My Maps"):
                                            st.markdown("""
                                            ### How to Import into Google My Maps:
                                            1. Go to [Google My Maps](https://www.google.com/mymaps).
                                            2. Click **Create a new map**.
                                            3. In the new map, click **Import** under the layer section.
                                            4. Upload the downloaded CSV file(s) or extract from ZIP.
                                            5. Set the following:
                                               - **Placemarker Pins**: Select the `ADDRESS` column.
                                               - **Placemarker Name (Title)**: Combine `FIRST_NAME` and `LAST_NAME` or use `DATA` column.
                                            6. Dismiss any locations that result in an error during import.
                                            7. Zoom out and manually delete any pins that are significantly distant from the main cluster.
                                            """)
                                        
                                        progress_bar.progress(1.0)
                                
                                # BUSINESS ADDRESS + FIRST NAME LAST NAME
                                elif option == "Business Address + First Name Last Name":
                                        processing_text.text("Processing business addresses with names...")
                                        
                                        # Determine which business address column to use
                                        business_address_col = None
                                        business_city_col = None
                                        business_state_col = None
                                        business_zip_col = None
                                        
                                        if 'COMPANY_ADDRESS' in df.columns:
                                            business_address_col = 'COMPANY_ADDRESS'
                                            business_city_col = 'COMPANY_CITY' if 'COMPANY_CITY' in df.columns else None
                                            business_state_col = 'COMPANY_STATE' if 'COMPANY_STATE' in df.columns else None
                                            business_zip_col = 'COMPANY_ZIP' if 'COMPANY_ZIP' in df.columns else None
                                        elif 'PROFESSIONAL_ADDRESS' in df.columns:
                                            business_address_col = 'PROFESSIONAL_ADDRESS'
                                            business_city_col = 'PROFESSIONAL_CITY' if 'PROFESSIONAL_CITY' in df.columns else None
                                            business_state_col = 'PROFESSIONAL_STATE' if 'PROFESSIONAL_STATE' in df.columns else None
                                            business_zip_col = 'PROFESSIONAL_ZIP' if 'PROFESSIONAL_ZIP' in df.columns else None
                                        
                                        # Filter to rows with business addresses
                                        df = df[df[business_address_col].notna()]
                                        
                                        # Clean business addresses
                                        if st.session_state['user_preferences']['auto_clean_addresses']:
                                            processing_text.text("Cleaning business addresses...")
                                            df['BUSINESS_ADDRESS_CLEAN'] = df[business_address_col].apply(clean_address)
                                            progress_bar.progress(0.3)
                                            business_address_display = 'BUSINESS_ADDRESS_CLEAN'
                                        else:
                                            business_address_display = business_address_col
                                        
                                        # Create the business address field
                                        address_components = [business_address_display]
                                        if business_city_col and business_city_col in df.columns:
                                            address_components.append(business_city_col)
                                        if business_state_col and business_state_col in df.columns:
                                            address_components.append(business_state_col)
                                        if business_zip_col and business_zip_col in df.columns:
                                            address_components.append(business_zip_col)
                                        
                                        # Create the full business address
                                        df['BUSINESS_ADDRESS'] = df[address_components].apply(
                                            lambda row: ', '.join([str(x) for x in row if pd.notna(x) and x != '']), axis=1
                                        )
                                        
                                        progress_bar.progress(0.6)
                                        
                                        # Create output with names and business address
                                        output_df = df[['FIRST_NAME', 'LAST_NAME', 'BUSINESS_ADDRESS']].copy()
                                        
                                        # Add additional business info if available
                                        if 'COMPANY_NAME' in df.columns:
                                            output_df['COMPANY_NAME'] = df['COMPANY_NAME']
                                        if 'JOB_TITLE' in df.columns:
                                            output_df['JOB_TITLE'] = df['JOB_TITLE']
                                        if 'COMPANY_INDUSTRY' in df.columns:
                                            output_df['COMPANY_INDUSTRY'] = df['COMPANY_INDUSTRY']
                                        
                                        st.success(f"✅ Processing complete! Generated {len(output_df):,} rows with names and business addresses")
                                        
                                        # Show data summary
                                        complete_records = sum(
                                            output_df['FIRST_NAME'].notna() & 
                                            output_df['LAST_NAME'].notna() & 
                                            output_df['BUSINESS_ADDRESS'].notna() & 
                                            (output_df['BUSINESS_ADDRESS'] != '')
                                        )
                                        st.write(f"**Complete records (with name and business address):** {complete_records:,} ({complete_records/len(output_df)*100:.1f}%)")
                                        
                                        # Show source information
                                        source_info = f"**Business addresses sourced from:** {business_address_col}"
                                        if business_city_col or business_state_col or business_zip_col:
                                            additional_cols = [col for col in [business_city_col, business_state_col, business_zip_col] if col]
                                            source_info += f" (with {', '.join(additional_cols)})"
                                        st.info(source_info)
                                        
                                        # Show additional columns included
                                        additional_cols = [col for col in ['COMPANY_NAME', 'JOB_TITLE', 'COMPANY_INDUSTRY'] if col in output_df.columns]
                                        if additional_cols:
                                            st.write(f"**Additional business data included:** {', '.join(additional_cols)}")
                                        
                                        # Provide download options
                                        output_format = st.radio("Output format:", 
                                                               ("CSV", "Excel", "JSON"), 
                                                               horizontal=True)
                                        
                                        create_download_button(
                                            output_df,
                                            "business_address_names",
                                            output_format.lower(),
                                            f"Download {len(output_df):,} records with names and business addresses"
                                        )
                                        
                                        # Add Google My Maps instructions
                                        with st.expander("How to Import into Google My Maps"):
                                            st.markdown("""
                                            ### How to Import into Google My Maps:
                                            1. Go to [Google My Maps](https://www.google.com/mymaps).
                                            2. Click **Create a new map**.
                                            3. In the new map, click **Import** under the layer section.
                                            4. Upload the downloaded CSV file(s) or extract from ZIP.
                                            5. Set the following:
                                               - **Placemarker Pins**: Select the `BUSINESS_ADDRESS` column.
                                               - **Placemarker Name (Title)**: Combine `FIRST_NAME` and `LAST_NAME`, or use `COMPANY_NAME` if available.
                                            6. Dismiss any locations that result in an error during import.
                                            7. Zoom out and manually delete any pins that are significantly distant from the main cluster.
                                            """)
                                        
                                        progress_bar.progress(1.0)
                                
                                # DUPLICATE ANALYSIS & FREQUENCY COUNTER
                                elif option == "Duplicate Analysis & Frequency Counter":
                                        processing_text.text("Analyzing duplicate records and calculating frequencies...")
                                        
                                        # Make a copy to avoid modifying the original
                                        analysis_df = df.copy()
                                        
                                        progress_bar.progress(0.1)
                                        
                                        # User interface for duplicate detection method
                                        st.subheader("Duplicate Detection Configuration")
                                        
                                        duplicate_method = st.radio(
                                            "How should duplicates be detected?",
                                            ["All columns (exact match)", "Selected columns only"],
                                            help="Choose whether to compare all columns or select specific ones for duplicate detection"
                                        )
                                        
                                        columns_for_comparison = []
                                        
                                        if duplicate_method == "Selected columns only":
                                            # Let user select which columns to use for duplicate detection
                                            available_columns = analysis_df.columns.tolist()
                                            columns_for_comparison = st.multiselect(
                                                "Select columns to use for duplicate detection:",
                                                options=available_columns,
                                                default=available_columns[:3] if len(available_columns) >= 3 else available_columns,
                                                help="Records will be considered duplicates if they match on ALL selected columns"
                                            )
                                            
                                            if not columns_for_comparison:
                                                st.error("Please select at least one column for duplicate detection.")
                                                st.stop()
                                        else:
                                            # Use all columns
                                            columns_for_comparison = analysis_df.columns.tolist()
                                        
                                        # Sort order preference
                                        sort_order = st.radio(
                                            "Sort order:",
                                            ["Most frequent first (descending)", "Least frequent first (ascending)"],
                                            help="Choose how to sort the final results by frequency count"
                                        )
                                        
                                        if st.button("Analyze Duplicates"):
                                            processing_text.text("Counting record frequencies...")
                                            progress_bar.progress(0.3)
                                            
                                            # Create a subset for duplicate detection if using selected columns
                                            if duplicate_method == "Selected columns only":
                                                comparison_df = analysis_df[columns_for_comparison]
                                            else:
                                                comparison_df = analysis_df
                                            
                                            # Count frequencies using value_counts on the combination of selected columns
                                            if len(columns_for_comparison) == 1:
                                                # Single column comparison - handle NaN values properly
                                                analysis_df['temp_key'] = analysis_df[columns_for_comparison[0]].fillna('MISSING').astype(str)
                                                frequency_counts = analysis_df['temp_key'].value_counts()
                                            else:
                                                # Multiple column comparison - create a composite key
                                                # Handle NaN values and ensure proper string conversion
                                                analysis_df['temp_key'] = comparison_df.apply(
                                                    lambda row: '|'.join([str(val) if pd.notna(val) else 'MISSING' for val in row]), axis=1
                                                )
                                                frequency_counts = analysis_df['temp_key'].value_counts()
                                            
                                            progress_bar.progress(0.5)
                                            
                                            # Map frequency counts back to the original data
                                            processing_text.text("Adding frequency counts to records...")
                                            analysis_df['FREQUENCY_COUNT'] = analysis_df['temp_key'].map(frequency_counts)
                                            
                                            # Remove the temporary key column
                                            analysis_df = analysis_df.drop('temp_key', axis=1)
                                            
                                            progress_bar.progress(0.7)
                                            
                                            # Remove duplicates - keep first occurrence of each unique record
                                            processing_text.text("Removing duplicates...")
                                            if duplicate_method == "Selected columns only":
                                                unique_df = analysis_df.drop_duplicates(subset=columns_for_comparison, keep='first')
                                            else:
                                                unique_df = analysis_df.drop_duplicates(keep='first')
                                            
                                            progress_bar.progress(0.8)
                                            
                                            # Sort by frequency count
                                            processing_text.text("Sorting by frequency...")
                                            ascending_order = sort_order.startswith("Least frequent")
                                            unique_df = unique_df.sort_values('FREQUENCY_COUNT', ascending=ascending_order)
                                            
                                            # Reorder columns to put FREQUENCY_COUNT first
                                            cols = ['FREQUENCY_COUNT'] + [col for col in unique_df.columns if col != 'FREQUENCY_COUNT']
                                            output_df = unique_df[cols].reset_index(drop=True)
                                            
                                            progress_bar.progress(0.9)
                                            
                                            # Display results
                                            st.success(f"✅ Duplicate analysis complete! Processed {len(analysis_df):,} original records")
                                            
                                            # Show comprehensive statistics
                                            st.subheader("Analysis Results")
                                            
                                            # Summary metrics
                                            col1, col2, col3, col4 = st.columns(4)
                                            with col1:
                                                st.metric("Original Records", f"{len(analysis_df):,}")
                                            with col2:
                                                st.metric("Unique Records", f"{len(output_df):,}")
                                            with col3:
                                                duplicates_removed = len(analysis_df) - len(output_df)
                                                st.metric("Duplicates Removed", f"{duplicates_removed:,}")
                                            with col4:
                                                duplicate_rate = (duplicates_removed / len(analysis_df) * 100) if len(analysis_df) > 0 else 0
                                                st.metric("Duplicate Rate", f"{duplicate_rate:.1f}%")
                                            
                                            # Show detection method used
                                            st.info(f"**Duplicate detection method:** {duplicate_method}")
                                            if duplicate_method == "Selected columns only":
                                                st.write(f"**Columns used for comparison:** {', '.join(columns_for_comparison)}")
                                            
                                            # Show frequency distribution
                                            with st.expander("Frequency Distribution Analysis"):
                                                freq_stats = output_df['FREQUENCY_COUNT'].describe()
                                                
                                                col1, col2 = st.columns(2)
                                                with col1:
                                                    st.write("**Frequency Statistics:**")
                                                    st.dataframe(freq_stats.to_frame("Value"), use_container_width=True)
                                                
                                                with col2:
                                                    st.write("**Top 10 Most Frequent Records:**")
                                                    top_frequent = output_df.head(10)[['FREQUENCY_COUNT'] + columns_for_comparison[:3]]
                                                    st.dataframe(top_frequent, use_container_width=True)
                                                
                                                # Frequency distribution chart
                                                freq_distribution = output_df['FREQUENCY_COUNT'].value_counts().sort_index()
                                                st.write("**Distribution of Frequency Counts:**")
                                                st.bar_chart(freq_distribution)
                                            
                                            # Show sample of results
                                            with st.expander("Sample of Results (Top 10 Records)"):
                                                st.dataframe(output_df.head(10), use_container_width=True)
                                            
                                            # Records that appeared only once
                                            unique_records = len(output_df[output_df['FREQUENCY_COUNT'] == 1])
                                            if unique_records > 0:
                                                st.write(f"📊 **Records appearing only once:** {unique_records:,} ({unique_records/len(output_df)*100:.1f}% of unique records)")
                                            
                                            # Records that appeared multiple times
                                            duplicate_records = len(output_df[output_df['FREQUENCY_COUNT'] > 1])
                                            if duplicate_records > 0:
                                                st.write(f"🔄 **Records with duplicates:** {duplicate_records:,} ({duplicate_records/len(output_df)*100:.1f}% of unique records)")
                                                max_frequency = output_df['FREQUENCY_COUNT'].max()
                                                st.write(f"📈 **Highest frequency count:** {max_frequency}")
                                            
                                            # Provide download options
                                            st.subheader("Download Results")
                                            output_format = st.radio("Output format:", 
                                                                   ("CSV", "Excel", "JSON"), 
                                                                   horizontal=True)
                                            
                                            create_download_button(
                                                output_df,
                                                "duplicate_analysis_results",
                                                output_format.lower(),
                                                f"Download {len(output_df):,} unique records with frequency counts"
                                            )
                                            
                                            # Usage tips
                                            with st.expander("💡 How to Use These Results"):
                                                st.markdown("""
                                                **Understanding Your Results:**
                                                - **FREQUENCY_COUNT**: Shows how many times each record appeared in your original data
                                                - **High frequency records**: May indicate common entries, popular items, or data quality issues
                                                - **Single occurrence records**: Unique entries that appeared only once
                                                
                                                **Common Use Cases:**
                                                - **Data Quality**: Identify frequently duplicated records that need cleanup
                                                - **Popular Analysis**: Find most common entries (customers, products, etc.)
                                                - **Deduplication**: Clean dataset with frequency information preserved
                                                - **Pattern Recognition**: Understand data distribution patterns
                                                """)
                                            
                                            progress_bar.progress(1.0)
                                
                                # If no matching option is found
                                else:
                                        st.error(f"Processing logic for '{option}' is not yet implemented. Please select a different option.")
                                        st.info("Available options with full implementations:")
                                        implemented_options = [
                                            "Address + HoNWIncome", "Address + HoNWIncome & Phone",
                                            "Address + HoNWIncome First Name Last Name", "Business Address + First Name Last Name",
                                            "Full Combined Address", "Phone & Credit Score", "Complete Contact Export",
                                            "ZIP Split: Address+HoNW", "ZIP Split: Address+HoNW+Phone",
                                            "File Combiner and Batcher", "Sha256", "Split by State",
                                            "B2B Job Titles Focus", "Filter by Zip Codes", "Company Industry",
                                            "Duplicate Analysis & Frequency Counter", "DNC Phone Number Cleaner"
                                        ]
                                        for opt in implemented_options:
                                            st.write(f"• {opt}")
    
    with tab2:
        st.header("📊 Data Insights & Visualization")
        
        # Check if there's processed data to visualize
        if 'processed_data' in st.session_state:
            df_viz = st.session_state['processed_data']
            
            st.subheader("Dataset Overview")
            
            # Basic statistics
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Total Records", f"{len(df_viz):,}")
            with col2:
                st.metric("Total Columns", f"{len(df_viz.columns):,}")
            with col3:
                completeness = (df_viz.count().sum() / (len(df_viz) * len(df_viz.columns)) * 100)
                st.metric("Data Completeness", f"{completeness:.1f}%")
            
            # Column completeness chart
            st.subheader("Column Completeness Analysis")
            col_completeness = (df_viz.count() / len(df_viz) * 100).sort_values(ascending=True)
            st.bar_chart(col_completeness)
            
            # Data quality insights
            st.subheader("Data Quality Insights")
            
            # Check for common data quality issues
            quality_issues = []
            
            # Missing data
            missing_data_pct = (df_viz.isnull().sum() / len(df_viz) * 100)
            high_missing = missing_data_pct[missing_data_pct > 50]
            if len(high_missing) > 0:
                quality_issues.append(f"📊 {len(high_missing)} columns have >50% missing data")
            
            # Duplicate rows
            duplicates = df_viz.duplicated().sum()
            if duplicates > 0:
                quality_issues.append(f"🔄 {duplicates:,} duplicate rows found ({duplicates/len(df_viz)*100:.1f}%)")
            
            # Phone number patterns (if phone columns exist)
            phone_cols = [col for col in df_viz.columns if 'PHONE' in col.upper()]
            if phone_cols:
                for col in phone_cols:
                    if col in df_viz.columns:
                        # Safely convert to string and handle NaN values before using .str accessor
                        phone_series = df_viz[col].fillna('').astype(str)
                        valid_phones = phone_series.str.match(r'^\(\d{3}\) \d{3}-\d{4}$').sum()
                        total_phones = df_viz[col].notna().sum()
                        if total_phones > 0:
                            quality_issues.append(f"📞 {col}: {valid_phones}/{total_phones} ({valid_phones/total_phones*100:.1f}%) properly formatted")
            
            if quality_issues:
                for issue in quality_issues:
                    st.write(f"• {issue}")
            else:
                st.success("✅ No major data quality issues detected!")
                
        else:
            # Show sample visualizations and features when no data is loaded
            st.info("📈 Upload and process a file to see detailed data visualizations and insights!")
            
            st.subheader("Available Visualizations")
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.write("**📊 Data Quality Metrics**")
                st.write("• Column completeness analysis")
                st.write("• Missing data patterns")
                st.write("• Duplicate detection")
                st.write("• Data format validation")
                
                st.write("**🗺️ Geographic Insights**")
                st.write("• State distribution charts")
                st.write("• ZIP code coverage maps")
                st.write("• Address completion rates")
            
            with col2:
                st.write("**📱 Contact Data Analysis**")
                st.write("• Phone number format validation")
                st.write("• Email domain analysis")
                st.write("• DNC status distribution")
                
                st.write("**🏢 Business Data Insights**")
                st.write("• Industry distribution")
                st.write("• Job title frequency")
                st.write("• Company size analysis")
            
            # Sample charts placeholder
            st.subheader("Sample Data Quality Dashboard")
            
            # Create sample data for demonstration
            import numpy as np
            
            # Sample completeness chart
            sample_columns = ['FIRST_NAME', 'LAST_NAME', 'PERSONAL_ADDRESS', 'PERSONAL_CITY', 
                            'PERSONAL_STATE', 'MOBILE_PHONE', 'BUSINESS_EMAIL', 'COMPANY_NAME']
            sample_completeness = np.random.uniform(60, 95, len(sample_columns))
            
            completeness_data = pd.DataFrame({
                'Column': sample_columns,
                'Completeness %': sample_completeness
            }).set_index('Column')
            
            st.write("**Sample Column Completeness Analysis:**")
            st.bar_chart(completeness_data)
            
            # Sample state distribution
            sample_states = ['CA', 'TX', 'FL', 'NY', 'PA', 'IL', 'OH', 'GA', 'NC', 'MI']
            sample_counts = np.random.randint(100, 1000, len(sample_states))
            
            state_data = pd.DataFrame({
                'State': sample_states,
                'Records': sample_counts
            }).set_index('State')
            
            st.write("**Sample State Distribution:**")
            st.bar_chart(state_data)
            
            st.markdown("""
            ### 💡 How to Use Data Visualizations:
            
            1. **Upload your CSV file** in the Process tab
            2. **Select any processing option** to analyze your data
            3. **Return to this tab** to see detailed insights
            4. **Use the insights** to:
               - Identify data quality issues
               - Understand your dataset composition
               - Make informed decisions about processing options
               - Optimize your data for better results
            
            **Pro Tips:**
            - Higher completeness percentages indicate better data quality
            - Look for patterns in missing data to identify collection issues
            - Use geographic distribution to plan targeted campaigns
            - Monitor phone/email format compliance for better deliverability
            """)

    with tab3:
        st.header("Frequently Asked Questions")
        
        faq_items = [
            ("What types of files can I process?", "Currently, the app accepts CSV files. Make sure your data has the required columns for each operation."),
            ("How do I prepare my data?", "Ensure your CSV has headers and the relevant columns for your chosen operation. Check the operation description for required columns."),
            ("Why are my addresses not being cleaned properly?", "The address cleaner works best with standardized US addresses. Some complex or non-standard addresses might not be parsed correctly."),
            ("Can I process international addresses?", "The cleaner is optimized for US addresses but will work with many international formats. Results may vary for non-US addresses."),
            ("What is the maximum file size?", "The recommended maximum is 200MB, but processing time will increase with larger files."),
            ("How do I import results into Google My Maps?", "For address-related outputs: 1) Go to Google My Maps, 2) Click 'Create a new map', 3) Click 'Import' under layers, 4) Upload the CSV, 5) For placemarker pins, select the address column, 6) For placemarker name, select the desired column."),
            ("Why are my phone numbers not formatting correctly?", "The app tries to standardize 10-digit US phone numbers. International or non-standard formats might not be handled properly."),
            ("How do I filter by multiple criteria?", "For complex filtering, consider using the 'Company Industry' option as a template and adapt your workflow - process in steps using intermediate files.")
        ]
        
        for question, answer in faq_items:
            with st.expander(question):
                st.write(answer)
        
        st.info("If you have additional questions or encounter issues, please report them to improve the application.")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        st.error(f"An unexpected error occurred: {str(e)}")
        logger.error("Application error", exc_info=True)