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
            "Sha256",
            "Complete Contact Export"
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
            "ZIP Split: Address+HoNW": "Splits the cleaned address and homeowner data into separate files based on ZIP codes.",
            "ZIP Split: Address+HoNW+Phone": "Splits the cleaned address, homeowner data, and phone numbers into separate files based on ZIP codes.",
            "File Combiner and Batcher": "Combines multiple uploaded CSV files and splits the result into customizable-sized batches.",
            "Sha256": "Provides names with hashed email data, preferring personal email hash.",
            "Full Combined Address": "Generates a comprehensive dataset with full address and additional metadata.",
            "Phone & Credit Score": "Focuses on phone numbers and credit scores with address details.",
            "Split by State": "Splits the dataset into one file per state based on the PERSONAL_STATE column.",
            "B2B Job Titles Focus": "Extracts B2B job title data with company and professional details into a single file.",
            "Filter by Zip Codes": "Filters the data to include only rows where the first 5 digits of PERSONAL_ZIP match the provided 5-digit zip codes.",
            "Company Industry": "Filters data by unique industries from the COMPANY_INDUSTRY column, allowing multi-selection for efficient filtering.",
            "Complete Contact Export": "Processes and cleans the entire contact file, formatting phone numbers and addresses while preserving all original data. Maintains the original structure for compatibility with other systems."
        }

        if option != "Select an option":
            st.info(descriptions[option])
            
            # File uploader and option-specific inputs
            if option == "File Combiner and Batcher":
                # Multiple file upload for combiner
                uploaded_files = st.file_uploader("Upload multiple CSV files", type=["csv"], accept_multiple_files=True)
                batch_size = st.number_input("Batch size (rows)", min_value=100, max_value=10000, 
                                            value=st.session_state['user_preferences']['batch_size'], step=100)
                
                if uploaded_files and st.button("Combine and Batch Files"):
                    with st.spinner("Combining files..."):
                        # Initialize combined DataFrame
                        combined_df = pd.DataFrame()
                        
                        # Show progress for each file
                        progress_bar = st.progress(0)
                        
                        for i, file in enumerate(uploaded_files):
                            try:
                                temp_df = pd.read_csv(file)
                                combined_df = pd.concat([combined_df, temp_df], ignore_index=True)
                                progress_bar.progress((i + 1) / len(uploaded_files))
                            except Exception as e:
                                st.error(f"Error processing file {file.name}: {str(e)}")
                        
                        if combined_df.empty:
                            st.error("No data found in the uploaded files.")
                        else:
                            st.success(f"✅ Combined {len(uploaded_files)} files with {len(combined_df):,} total rows")
                            
                            # Show preview of combined data
                            if st.session_state['user_preferences']['show_preview']:
                                show_data_preview(combined_df, option, 
                                                max_rows=st.session_state['user_preferences']['max_preview_rows'])
                            
                            # Determine if batching is needed
                            needs_batching = len(combined_df) > batch_size
                            
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
                    
                # Process button for all other options
                if uploaded_file and option != "Company Industry":
                    if st.button("Process Data"):
                        with st.spinner("Processing file..."):
                            # Read the uploaded file
                            try:
                                df = pd.read_csv(uploaded_file)
                                st.success(f"File loaded with {len(df):,} rows and {len(df.columns):,} columns")
                                
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
                                    valid, msg = validate_columns(df, ['PERSONAL_ADDRESS', 'PERSONAL_CITY', 'MOBILE_PHONE', 'DNC'], option)
                                elif option == "Sha256":
                                    valid, msg = validate_columns(df, ['FIRST_NAME', 'LAST_NAME', 'SHA256_PERSONAL_EMAIL', 'SHA256_BUSINESS_EMAIL'], option)
                                elif option == "Full Combined Address":
                                    valid, msg = validate_columns(df, ['FIRST_NAME', 'LAST_NAME', 'PERSONAL_ADDRESS', 'PERSONAL_CITY', 'PERSONAL_STATE', 'PERSONAL_ZIP'], option)
                                elif option == "Phone & Credit Score":
                                    valid, msg = validate_columns(df, ['FIRST_NAME', 'LAST_NAME', 'PERSONAL_ADDRESS', 'PERSONAL_CITY', 'PERSONAL_STATE', 'PERSONAL_ZIP'], option)
                                    # Special check for phone number columns
                                    if valid and 'MOBILE_PHONE' not in df.columns and 'DIRECT_NUMBER' not in df.columns:
                                        valid = False
                                        msg = "CSV file must contain at least one of 'MOBILE_PHONE' or 'DIRECT_NUMBER'."
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
                                    
                                    # FILTER BY ZIP CODES
                                    if option == "Filter by Zip Codes":
                                        if zip_codes_input:
                                            processing_text.text("Filtering by zip codes...")
                                            
                                            # Ensure PERSONAL_ZIP is string to preserve leading zeros
                                            df['PERSONAL_ZIP'] = df['PERSONAL_ZIP'].astype(str)
                                            
                                            # Create temporary column with first 5 digits, stripping spaces
                                            df['PERSONAL_ZIP_5'] = df['PERSONAL_ZIP'].str.strip().str[:5]
                                            
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
                                            df['PERSONAL_ZIP'] = df['PERSONAL_ZIP'].astype(str).str.strip()
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
                                    
                                    # ADDRESS + HONWINCOME
                                    elif option == "Address + HoNWIncome":
                                        processing_text.text("Processing addresses with homeowner, net worth, and income data...")
                                        
                                        # Clean the data
                                        if st.session_state['user_preferences']['auto_clean_addresses']:
                                            df = df[df['PERSONAL_ADDRESS'].notna()]
                                            df['PERSONAL_ADDRESS_CLEAN'] = df['PERSONAL_ADDRESS'].apply(clean_address)
                                            progress_bar.progress(0.2)
                                        
                                        # Create the address components
                                        address_components = ['PERSONAL_ADDRESS_CLEAN']
                                        if 'PERSONAL_CITY' in df.columns:
                                            address_components.append('PERSONAL_CITY')
                                        if 'PERSONAL_STATE' in df.columns:
                                            address_components.append('PERSONAL_STATE')
                                        
                                        # Create the address field
                                        df['ADDRESS'] = df[address_components].apply(
                                            lambda row: ', '.join([str(x) for x in row if pd.notna(x) and x != '']), axis=1
                                        )
                                        
                                        # Handle missing values
                                        df['HOMEOWNER'] = df['HOMEOWNER'].fillna('')
                                        df['NET_WORTH'] = df['NET_WORTH'].fillna('')
                                        df['INCOME_RANGE'] = df['INCOME_RANGE'].fillna('')
                                        
                                        # Create the data field
                                        df['DATA'] = 'Ho ' + df['HOMEOWNER'] + ' | NW ' + df['NET_WORTH'] + ' | Income ' + df['INCOME_RANGE']
                                        
                                        # Final output
                                        output_df = df[['ADDRESS', 'DATA']]
                                        
                                        progress_bar.progress(0.6)
                                        
                                        # Check if we need to split the output
                                        batch_size = st.session_state['user_preferences']['batch_size']
                                        if len(output_df) > batch_size:
                                            processing_text.text(f"Splitting output into batches (max {batch_size:,} rows per file)...")
                                            
                                            # Split the DataFrame
                                            output_batches = split_dataframe(output_df, batch_size)
                                            batch_names = [f"address_honwincome_part_{i+1}" for i in range(len(output_batches))]
                                            
                                            st.success(f"✅ Processing complete! Split into {len(output_batches)} batches")
                                            
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
                                            
                                            # Provide download options
                                            output_format = st.radio("Output format:", 
                                                                   ("CSV", "Excel", "JSON"), 
                                                                   horizontal=True)
                                        
                                            # Single file download
                                            create_download_button(
                                                output_df,
                                                "address_honwincome",
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
                                    
                                    # ADDRESS + HONWINCOME & PHONE
                                    elif option == "Address + HoNWIncome & Phone":
                                        processing_text.text("Processing addresses with homeowner, net worth, income, and phone data...")
                                        
                                        # Clean the data
                                        if st.session_state['user_preferences']['auto_clean_addresses']:
                                            df = df[df['PERSONAL_ADDRESS'].notna()]
                                            df['PERSONAL_ADDRESS_CLEAN'] = df['PERSONAL_ADDRESS'].apply(clean_address)
                                            progress_bar.progress(0.2)
                                        
                                        # Create the address components
                                        address_components = ['PERSONAL_ADDRESS_CLEAN']
                                        if 'PERSONAL_CITY' in df.columns:
                                            address_components.append('PERSONAL_CITY')
                                        if 'PERSONAL_STATE' in df.columns:
                                            address_components.append('PERSONAL_STATE')
                                        
                                        # Create the address field
                                        df['ADDRESS'] = df[address_components].apply(
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
                                    
                                    # COMPLETE CONTACT EXPORT
                                    elif option == "Complete Contact Export":
                                        processing_text.text("Processing complete contact export...")
                                        
                                        # Make a copy to avoid modifying the original
                                        output_df = df.copy()
                                        
                                        # Check file size for memory optimization
                                        is_large_file = len(output_df) > 100000
                                        if is_large_file:
                                            st.info(f"📊 Large file detected ({len(output_df):,} rows). Using optimized processing to improve performance.")
                                            # Try to free memory
                                            clean_memory()
                                        
                                        # Define the expected columns in the correct order
                                        expected_columns = [
                                            'FIRST_NAME', 'LAST_NAME', 'DNC', 'MOBILE_PHONE', 'DIRECT_NUMBER', 
                                            'PERSONAL_PHONE', 'PERSONAL_ADDRESS', 'PERSONAL_CITY', 'PERSONAL_STATE', 
                                            'PERSONAL_ZIP', 'AGE_RANGE', 'CHILDREN', 'GENDER', 'HOMEOWNER', 
                                            'MARRIED', 'NET_WORTH', 'INCOME_RANGE', 'PERSONAL_EMAIL', 
                                            'ADDITIONAL_PERSONAL_EMAILS', 'SKIPTRACE_B2B_PHONE', 
                                            'SKIPTRACE_B2B_SOURCE', 'SKIPTRACE_B2B_WEBSITE',
                                            'SKIPTRACE_B2B_COMPANY_NAME', 'JOB_TITLE', 'DEPARTMENT', 
                                            'SENIORITY_LEVEL', 'JOB_TITLE_LAST_UPDATED', 'LINKEDIN_URL', 
                                            'BUSINESS_EMAIL', 'COMPANY_NAME', 'COMPANY_ADDRESS', 
                                            'COMPANY_DOMAIN', 'COMPANY_EMPLOYEE_COUNT', 'COMPANY_LINKEDIN_URL', 
                                            'COMPANY_PHONE', 'COMPANY_REVENUE', 'COMPANY_SIC', 'COMPANY_NAICS', 
                                            'COMPANY_CITY', 'COMPANY_STATE', 'COMPANY_ZIP', 'COMPANY_INDUSTRY',
                                            'PROFESSIONAL_ADDRESS', 'PROFESSIONAL_ADDRESS_2', 'PROFESSIONAL_CITY', 
                                            'PROFESSIONAL_STATE', 'PROFESSIONAL_ZIP', 'PROFESSIONAL_ZIP4'
                                        ]
                                        
                                        # Enhanced error handling for missing critical columns
                                        if not any(col in output_df.columns for col in ['FIRST_NAME', 'LAST_NAME']):
                                            st.warning("⚠️ Input file appears to be missing essential name columns. Output may not be as expected.")
                                        
                                        # Create a new DataFrame with only the expected columns that exist in the input
                                        # and in the expected order
                                        columns_to_keep = [col for col in expected_columns if col in output_df.columns]
                                        filtered_df = output_df[columns_to_keep].copy()
                                        
                                        # Add column reorganization preview
                                        with st.expander("Column Reorganization Preview"):
                                            col1, col2 = st.columns(2)
                                            with col1:
                                                st.write("**Original Columns**")
                                                original_cols = pd.DataFrame({"Original": output_df.columns.tolist()})
                                                st.dataframe(original_cols, height=300)
                                            with col2:
                                                st.write("**Exported Columns (Rearranged)**")
                                                new_cols = pd.DataFrame({"Exported": filtered_df.columns.tolist()})
                                                st.dataframe(new_cols, height=300)
                                                
                                            # Show which columns were dropped
                                            dropped_cols = [col for col in output_df.columns if col not in filtered_df.columns]
                                            if dropped_cols:
                                                st.write("**Columns Being Dropped:**")
                                                st.write(", ".join(dropped_cols))
                                        
                                        # Set progress details for large files
                                        progress_detail = st.empty()
                                        if len(filtered_df) > 10000:
                                            progress_detail.text(f"Processing large file with {len(filtered_df):,} records...")
                                        
                                        # Clean addresses if requested
                                        if st.session_state['user_preferences']['auto_clean_addresses']:
                                            if 'PERSONAL_ADDRESS' in filtered_df.columns and filtered_df['PERSONAL_ADDRESS'].notna().any():
                                                processing_text.text("Cleaning addresses...")
                                                cleaned_count = 0
                                                
                                                # Process in chunks for large datasets
                                                chunk_size = 5000
                                                for i in range(0, len(filtered_df), chunk_size):
                                                    end_idx = min(i + chunk_size, len(filtered_df))
                                                    chunk = filtered_df.iloc[i:end_idx]
                                                    
                                                    # Update progress for large files
                                                    if len(filtered_df) > 10000:
                                                        progress_detail.text(f"Cleaning addresses... ({i:,} of {len(filtered_df):,} records)")
                                                    
                                                    # Apply cleaning to this chunk
                                                    mask = chunk['PERSONAL_ADDRESS'].notna()
                                                    chunk.loc[mask, 'PERSONAL_ADDRESS'] = chunk.loc[mask, 'PERSONAL_ADDRESS'].apply(
                                                        lambda x: clean_address(x) if pd.notna(x) else x
                                                    )
                                                    filtered_df.iloc[i:end_idx] = chunk
                                                    cleaned_count += mask.sum()
                                                
                                                st.info(f"Cleaned {cleaned_count:,} addresses.")
                                            
                                            # Also clean professional addresses if present
                                            if 'PROFESSIONAL_ADDRESS' in filtered_df.columns and filtered_df['PROFESSIONAL_ADDRESS'].notna().any():
                                                filtered_df['PROFESSIONAL_ADDRESS'] = filtered_df['PROFESSIONAL_ADDRESS'].apply(lambda x: clean_address(x) if pd.notna(x) else x)
                                                
                                            if 'COMPANY_ADDRESS' in filtered_df.columns and filtered_df['COMPANY_ADDRESS'].notna().any():
                                                filtered_df['COMPANY_ADDRESS'] = filtered_df['COMPANY_ADDRESS'].apply(lambda x: clean_address(x) if pd.notna(x) else x)
                                        
                                        # Format phone numbers if needed
                                        phone_columns = ['MOBILE_PHONE', 'DIRECT_NUMBER', 'PERSONAL_PHONE', 'COMPANY_PHONE']
                                        formatted_phones = 0
                                        
                                        for phone_col in phone_columns:
                                            if phone_col in filtered_df.columns:
                                                if len(filtered_df) > 10000:
                                                    progress_detail.text(f"Formatting {phone_col}...")
                                                
                                                # Format phone numbers in chunks for large datasets
                                                mask = filtered_df[phone_col].notna()
                                                filtered_df.loc[mask, phone_col] = filtered_df.loc[mask, phone_col].apply(validate_phone)
                                                formatted_phones += mask.sum()
                                        
                                        if formatted_phones > 0:
                                            st.info(f"Formatted {formatted_phones:,} phone numbers.")
                                        
                                        progress_bar.progress(0.6)
                                        
                                        # Determine output filename based on input file name
                                        input_filename = uploaded_file.name
                                        output_filename = input_filename
                                        
                                        if " - " in input_filename:
                                            # Try to preserve the naming convention if it exists
                                            output_filename = input_filename
                                        else:
                                            # Add " (output)" to the filename
                                            output_filename = input_filename.replace(".csv", "") + " (output).csv"
                                        
                                        # Add data validation metrics
                                        with st.expander("Data Quality Metrics"):
                                            metrics = []
                                            
                                            # Name validation
                                            if 'FIRST_NAME' in filtered_df.columns and 'LAST_NAME' in filtered_df.columns:
                                                missing_names = sum((filtered_df['FIRST_NAME'].isna()) | (filtered_df['LAST_NAME'].isna()))
                                                metrics.append(("Records missing name", missing_names, f"{missing_names/len(filtered_df)*100:.1f}%"))
                                            
                                            # Phone validation
                                            if 'MOBILE_PHONE' in filtered_df.columns:
                                                valid_phones = sum(filtered_df['MOBILE_PHONE'].str.match(r'^\(\d{3}\) \d{3}-\d{4}$', na=False))
                                                total_phones = sum(filtered_df['MOBILE_PHONE'].notna())
                                                if total_phones > 0:
                                                    metrics.append(("Valid phone numbers", valid_phones, f"{valid_phones/total_phones*100:.1f}%"))
                                            
                                            # Address validation
                                            if all(col in filtered_df.columns for col in ['PERSONAL_ADDRESS', 'PERSONAL_CITY', 'PERSONAL_STATE', 'PERSONAL_ZIP']):
                                                complete_addresses = sum(
                                                    filtered_df['PERSONAL_ADDRESS'].notna() & 
                                                    filtered_df['PERSONAL_CITY'].notna() & 
                                                    filtered_df['PERSONAL_STATE'].notna() & 
                                                    filtered_df['PERSONAL_ZIP'].notna()
                                                )
                                                metrics.append(("Complete addresses", complete_addresses, f"{complete_addresses/len(filtered_df)*100:.1f}%"))
                                            
                                            # DNC validation
                                            if 'DNC' in filtered_df.columns:
                                                dnc_count = sum(filtered_df['DNC'] == 'Y')
                                                metrics.append(("Do Not Call records", dnc_count, f"{dnc_count/len(filtered_df)*100:.1f}%"))
                                            
                                            # Display metrics in a table
                                            metrics_df = pd.DataFrame(metrics, columns=["Metric", "Count", "Percentage"])
                                            st.dataframe(metrics_df)
                                        
                                        # Success message
                                        st.success(f"✅ Processing complete! Prepared complete contact export with {len(filtered_df):,} rows")
                                        
                                        # Summary statistics
                                        cols = st.columns(3)
                                        with cols[0]:
                                            st.metric("Total Records", f"{len(filtered_df):,}")
                                        
                                        if 'MOBILE_PHONE' in filtered_df.columns:
                                            with cols[1]:
                                                phone_count = sum(filtered_df['MOBILE_PHONE'].notna())
                                                st.metric("Records with Phones", f"{phone_count:,}")
                                        
                                        if 'PERSONAL_ADDRESS' in filtered_df.columns:
                                            with cols[2]:
                                                address_count = sum(filtered_df['PERSONAL_ADDRESS'].notna())
                                                st.metric("Records with Addresses", f"{address_count:,}")
                                        
                                        # Provide download options
                                        output_format = st.radio("Output format:", 
                                                              ("CSV", "Excel", "JSON"), 
                                                              horizontal=True)
                                        
                                        # Create download button
                                        create_download_button(
                                            filtered_df,
                                            output_filename.replace(".csv", ""),  # Remove .csv extension as it's added by the function
                                            output_format.lower(),
                                            f"Download processed data with {len(filtered_df):,} rows"
                                        )
                                        
                                        progress_bar.progress(1.0)
                                        
                                        # Clear progress detail
                                        if len(filtered_df) > 10000:
                                            progress_detail.empty()
                                    
                            except Exception as e:
                                st.error(f"Error processing file: {str(e)}")
                                logger.error(f"Processing error: {str(e)}", exc_info=True)
                
                # Special handling for Company Industry
                elif uploaded_file and option == "Company Industry":
                    try:
                        df = pd.read_csv(uploaded_file)
                        st.success(f"File loaded with {len(df):,} rows and {len(df.columns):,} columns")
                        
                        # Check for required column
                        if 'COMPANY_INDUSTRY' not in df.columns:
                            st.error("CSV file must contain the 'COMPANY_INDUSTRY' column.")
                        else:
                            # Extract unique industries
                            unique_industries = sorted(df['COMPANY_INDUSTRY'].dropna().unique())
                            
                            if not unique_industries:
                                st.warning("No industries found in the 'COMPANY_INDUSTRY' column.")
                            else:
                                # Show industry stats
                                st.write(f"Found {len(unique_industries):,} unique industries")
                                
                                # Industry selection interface
                                st.subheader("Select Industries to Filter")
                                
                                # Add search box for industries
                                search_term = st.text_input("Search industries:", 
                                                          help="Type to search within industry names")
                                
                                # Filter industries by search term
                                if search_term:
                                    filtered_industries = [ind for ind in unique_industries 
                                                         if search_term.lower() in str(ind).lower()]
                                else:
                                    filtered_industries = unique_industries
                                
                                # Select all/none buttons
                                col1, col2 = st.columns(2)
                                with col1:
                                    if st.button("Select All"):
                                        if 'selected_industries' not in st.session_state:
                                            st.session_state['selected_industries'] = filtered_industries
                                        else:
                                            st.session_state['selected_industries'] = filtered_industries
                                

                                with col2:
                                    if st.button("Clear Selection"):
                                        if 'selected_industries' in st.session_state:
                                            st.session_state['selected_industries'] = []
                                
                                # Initialize selected_industries in session state if not already there
                                if 'selected_industries' not in st.session_state:
                                    st.session_state['selected_industries'] = []
                                
                                # Display multiselect with industries
                                selected_industries = st.multiselect(
                                    "Choose one or more industries:",
                                    options=filtered_industries,
                                    default=st.session_state['selected_industries'],
                                    help="Select multiple industries to include in the filtered output"
                                )
                                
                                # Update session state
                                st.session_state['selected_industries'] = selected_industries
                                
                                if st.button("Filter by Selected Industries"):
                                    if not selected_industries:
                                        st.error("Please select at least one industry to filter.")
                                    else:
                                        # Filter DataFrame based on selected industries
                                        filtered_df = df[df['COMPANY_INDUSTRY'].isin(selected_industries)]
                                        
                                        # Display results
                                        st.success("✅ Filtering complete!")
                                        st.write(f"Filtered to {len(filtered_df):,} rows based on {len(selected_industries)} selected industries")
                                        
                                        # Show summary of industry distribution
                                        with st.expander("Industry Distribution in Results"):
                                            industry_counts = filtered_df['COMPANY_INDUSTRY'].value_counts()
                                            count_df = pd.DataFrame({
                                                'Industry': industry_counts.index,
                                                'Count': industry_counts.values,
                                                'Percentage': industry_counts.values / len(filtered_df) * 100
                                            })
                                            st.dataframe(count_df, use_container_width=True)
                                        
                                        # Provide download options
                                        output_format = st.radio("Output format:", 
                                                               ("CSV", "Excel", "JSON"), 
                                                               horizontal=True)
                                        
                                        create_download_button(
                                            filtered_df, 
                                            "filtered_by_company_industry", 
                                            output_format.lower(),
                                            f"Download {len(filtered_df):,} filtered records"
                                        )
                                        
                                        st.info(
                                            "The output includes all columns from your original file, filtered to only include rows where "
                                            "COMPANY_INDUSTRY matches your selected industries."
                                        )
                    except Exception as e:
                        st.error(f"Error processing file: {str(e)}")
                        logger.error(f"Processing error: {str(e)}", exc_info=True)
    
    with tab2:
        st.header("Data Visualization")
        st.info("Upload a file to visualize data distributions and patterns.")
        
        # Simple visualization options
        uploaded_file_viz = st.file_uploader("Upload CSV for visualization", type=["csv"])
        
        if uploaded_file_viz:
            try:
                df_viz = pd.read_csv(uploaded_file_viz)
                st.success(f"File loaded with {len(df_viz):,} rows and {len(df_viz.columns):,} columns")
                
                # Select columns for visualization
                numeric_cols = df_viz.select_dtypes(include=['int64', 'float64']).columns.tolist()
                categorical_cols = df_viz.select_dtypes(include=['object', 'category']).columns.tolist()
                
                # Add visualization options here
                viz_type = st.selectbox(
                    "Select Visualization Type",
                    options=["Column Distribution", "Map View (if coordinates available)", "Data Summary"]
                )
                
                if viz_type == "Column Distribution":
                    if categorical_cols:
                        selected_col = st.selectbox("Select column to visualize", categorical_cols)
                        
                        # Limit to top N categories
                        top_n = st.slider("Show top N categories", 5, 50, 20)
                        
                        # Create distribution
                        value_counts = df_viz[selected_col].value_counts().head(top_n)
                        
                        st.subheader(f"Distribution of {selected_col} (Top {top_n})")
                        st.bar_chart(value_counts)
                        
                        # Show table of counts
                        st.dataframe(pd.DataFrame({
                            'Value': value_counts.index,
                            'Count': value_counts.values,
                            'Percentage': (value_counts.values / len(df_viz) * 100).round(2)
                        }))
                    else:
                        st.warning("No categorical columns found for distribution visualization.")
                
                elif viz_type == "Data Summary":
                    st.subheader("Data Summary")
                    
                    # Show basic stats for numeric columns
                    if numeric_cols:
                        st.write("**Numeric Columns Summary**")
                        st.dataframe(df_viz[numeric_cols].describe(), use_container_width=True)
                    
                    # Show categorical columns summary
                    if categorical_cols:
                        st.write("**Categorical Columns Summary**")
                        cat_summary = pd.DataFrame({
                            'Column': categorical_cols,
                            'Unique Values': [df_viz[col].nunique() for col in categorical_cols],
                            'Most Common': [df_viz[col].value_counts().index[0] if not df_viz[col].value_counts().empty else None for col in categorical_cols],
                            'Most Common %': [(df_viz[col].value_counts().iloc[0] / len(df_viz) * 100).round(2) if not df_viz[col].value_counts().empty else None for col in categorical_cols],
                            'Missing %': [(df_viz[col].isna().sum() / len(df_viz) * 100).round(2) for col in categorical_cols]
                        })
                        st.dataframe(cat_summary, use_container_width=True)
                
            except Exception as e:
                st.error(f"Error processing file for visualization: {str(e)}")
                logger.error(f"Visualization error: {str(e)}", exc_info=True)
    
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