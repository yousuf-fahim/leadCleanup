import streamlit as st
import pandas as pd
import usaddress
import io
import zipfile
from openpyxl import Workbook
import string

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
</style>
""", unsafe_allow_html=True)

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
def clean_address(address):
    """Parse and expand abbreviations in an address with a robust fallback."""
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


# Streamlit UI
st.sidebar.markdown("### Navigation")
options = [
    "Select an option",
    "Address + HoNWIncome",
    "Address + HoNWIncome & Phone",
    "ZIP Split: Address+HoNW",
    "ZIP Split: Address+HoNW+Phone",
    "File Combiner and Batcher",
    "Sha256",
    "Full Combined Address",
    "Phone & Credit Score",
    "Split by State",
    "B2B Job Titles Focus",
    "Filter by Zip Codes",
    "Company Industry"
]

option = st.sidebar.selectbox("Select Cleaning Option", options, index=0)

with st.container():
    st.title("📍 Address Cleaner")

    st.markdown(
        "[📥 Download Sample CSV](https://drive.google.com/file/d/19CdaLPNq7SUY1RgLdFD9gQI9JrSh/view?usp=sharing)",
        unsafe_allow_html=True)

    uploaded_file = st.file_uploader("Upload your CSV file (max 200MB)", type=["csv"], accept_multiple_files=False,
                                     help="Maximum file size: 200MB (depending on deployment environment)")

    descriptions = {
        "Address + HoNWIncome": "Combines cleaned address with homeowner status, net worth, and income range. Includes state if available.",
        "Address + HoNWIncome & Phone": "Adds phone number to the combined data if not marked as Do Not Call (DNC). Includes state if available.",
        "ZIP Split: Address+HoNW": "Splits the cleaned address and homeowner data into separate files based on ZIP codes.",
        "ZIP Split: Address+HoNW+Phone": "Splits the cleaned address, homeowner data, and phone numbers into separate files based on ZIP codes.",
        "File Combiner and Batcher": "Combines multiple uploaded CSV files and splits the result into 2,000-row batches.",
        "Sha256": "Provides names with hashed email data, preferring personal email hash.",
        "Full Combined Address": "Generates a comprehensive dataset with full address and additional metadata.",
        "Phone & Credit Score": "Focuses on phone numbers and credit scores with address details.",
        "Split by State": "Splits the dataset into one file per state based on the PERSONAL_STATE column.",
        "B2B Job Titles Focus": "Extracts B2B job title data with company and professional details into a single .xlsx file.",
        "Filter by Zip Codes": "Filters the data to include only rows where the first 5 digits of PERSONAL_ZIP match the provided 5-digit zip codes.",
        "Company Industry": "Filters data by unique industries from the COMPANY_INDUSTRY column (AQ), allowing multi-selection for efficient filtering."
    }

    if option != "Select an option":
        st.info(descriptions[option])

    # Add text area for zip codes with clear instruction
    if option == "Filter by Zip Codes":
        zip_codes_input = st.text_area("Enter 5-digit zip codes (separated by spaces, commas, or newlines)", height=100)
    else:
        zip_codes_input = None

    if option == "File Combiner and Batcher":
        if 'combined_df' not in st.session_state:
            st.session_state['combined_df'] = None
        if 'batched_files' not in st.session_state:
            st.session_state['batched_files'] = []

        uploaded_files = st.file_uploader("Upload multiple CSV files", type=["csv"], accept_multiple_files=True)

        if uploaded_files and st.button("Combine and Batch"):
            if len(uploaded_files) == 0:
                st.warning("No files were uploaded. Please upload one or more CSV files.")
                st.stop()
            combined_df = pd.DataFrame()
            for file in uploaded_files:
                temp_df = pd.read_csv(file)
                combined_df = pd.concat([combined_df, temp_df], ignore_index=True)
            if combined_df.empty:
                st.error("No data found in the uploaded files.")
                st.stop()

            st.session_state['combined_df'] = combined_df
            st.session_state['batched_files'] = []

            # Determine if batching is needed
            needs_batching = len(combined_df) > 2000

            if needs_batching:
                def split_dataframe(df, max_rows=2000):
                    return [df[i:i + max_rows] for i in range(0, len(df), max_rows)]

                split_dfs = split_dataframe(combined_df)
                for i, df_part in enumerate(split_dfs):
                    st.session_state['batched_files'].append((f"batch_{i + 1}", df_part))
                st.success(f"✅ Process complete! Data split into {len(split_dfs)} batches of 2,000 rows each.")
            else:
                st.session_state['batched_files'].append(("combined_file", combined_df))
                st.success("✅ Process complete! Your combined file is ready for download.")

        # Display download options if data is available
        if st.session_state['combined_df'] is not None:
            data_row_count = len(st.session_state['combined_df'])
            needs_batching = data_row_count > 2000

            if needs_batching:
                st.subheader(f"Download Options (Total: {data_row_count} rows)")
                # ZIP download for batched files
                zip_buffer = io.BytesIO()
                with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
                    for file_name, df_part in st.session_state['batched_files']:
                        csv_data = df_part.to_csv(index=False).encode('utf-8')
                        zip_file.writestr(f"{file_name}.csv", csv_data)
                zip_buffer.seek(0)
                st.download_button(
                    label="Download All Batches as ZIP",
                    data=zip_buffer.getvalue(),
                    file_name="batches.zip",
                    mime="application/zip",
                    key="download_zip"
                )

                # Individual batch downloads
                st.write("Or download individual batches:")
                
                # Use columns to create a grid layout for multiple download buttons
                batch_cols = st.columns(2)  # 2 columns for small screens
                for i, (file_name, df_part) in enumerate(st.session_state['batched_files']):
                    with batch_cols[i % 2]:  # Alternate between columns
                        st.download_button(
                            label=f"Download {file_name}.csv",
                            data=df_part.to_csv(index=False).encode('utf-8'),
                            file_name=f"{file_name}.csv",
                            mime="text/csv"
                        )
            else:
                # Single combined file download
                st.download_button(
                    label="Download Combined Data",
                    data=st.session_state['combined_df'].to_csv(index=False).encode('utf-8'),
                    file_name="combined_data.csv",
                    mime="text/csv"
                )

    elif option == "ZIP Split: Address+HoNW":
        zip_filter_input = st.text_area("Optionally enter zip codes to filter:", height=100)
        if uploaded_file and st.button("Process"):
            df = pd.read_csv(uploaded_file)
            df = df[df['PERSONAL_ADDRESS'].notna()]
            df['PERSONAL_ADDRESS_CLEAN'] = df['PERSONAL_ADDRESS'].apply(clean_address)
            df['ADDRESS'] = df[['PERSONAL_ADDRESS_CLEAN', 'PERSONAL_CITY', 'PERSONAL_STATE']].apply(
                lambda row: ', '.join([str(x) for x in row if pd.notna(x) and x != '']), axis=1)
            df['HOMEOWNER'] = df['HOMEOWNER'].fillna('')
            df['NET_WORTH'] = df['NET_WORTH'].fillna('')
            df['INCOME_RANGE'] = df['INCOME_RANGE'].fillna('')
            df['DATA'] = 'Ho ' + df['HOMEOWNER'] + ' | NW ' + df['NET_WORTH'] + ' | Income ' + df['INCOME_RANGE']
            if zip_filter_input.strip():
                zip_codes = [z.strip()[:5] for z in zip_filter_input.replace(",", " ").split() if z.strip()]
                df['PERSONAL_ZIP'] = df['PERSONAL_ZIP'].astype(str).str.strip()
                df = df[df['PERSONAL_ZIP'].str[:5].isin(zip_codes)]
            zip_buffer = io.BytesIO()
            with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
                for zip_code, group in df.groupby('PERSONAL_ZIP'):
                    csv_data = group[['ADDRESS', 'DATA']].to_csv(index=False).encode('utf-8')
                    zip_file.writestr(f"zip_{zip_code}.csv", csv_data)
            zip_buffer.seek(0)
            st.download_button("Download ZIP Split Files", zip_buffer.getvalue(),
                               "zip_split_address_honw.zip", "application/zip")
            st.success("✅ ZIP split (Address+HoNW) complete!")

    elif option == "ZIP Split: Address+HoNW+Phone":
        zip_filter_input = st.text_area("Optionally enter zip codes to filter:", height=100)
        if uploaded_file and st.button("Process"):
            df = pd.read_csv(uploaded_file)
            df = df[df['PERSONAL_ADDRESS'].notna()]
            df['PERSONAL_ADDRESS_CLEAN'] = df['PERSONAL_ADDRESS'].apply(clean_address)
            df['ADDRESS'] = df[['PERSONAL_ADDRESS_CLEAN', 'PERSONAL_CITY', 'PERSONAL_STATE']].apply(
                lambda row: ', '.join([str(x) for x in row if pd.notna(x) and x != '']), axis=1)
            df['MOBILE_PHONE'] = df['MOBILE_PHONE'].fillna('')
            df['DNC'] = df['DNC'].fillna('N')
            df['HOMEOWNER'] = df['HOMEOWNER'].fillna('')
            df['NET_WORTH'] = df['NET_WORTH'].fillna('')
            df['INCOME_RANGE'] = df['INCOME_RANGE'].fillna('')
            df['DATA'] = 'Ho ' + df['HOMEOWNER'] + ' | NW ' + df['NET_WORTH'] + ' | Income ' + df['INCOME_RANGE'] + \
                         df.apply(lambda row: ' | Phone ' + str(row['MOBILE_PHONE']) if (
                                 row['DNC'] != 'Y' and row['MOBILE_PHONE']) else '', axis=1)
            if zip_filter_input.strip():
                zip_codes = [z.strip()[:5] for z in zip_filter_input.replace(",", " ").split() if z.strip()]
                df['PERSONAL_ZIP'] = df['PERSONAL_ZIP'].astype(str).str.strip()
                df = df[df['PERSONAL_ZIP'].str[:5].isin(zip_codes)]
            zip_buffer = io.BytesIO()
            with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
                for zip_code, group in df.groupby('PERSONAL_ZIP'):
                    csv_data = group[['ADDRESS', 'DATA']].to_csv(index=False).encode('utf-8')
                    zip_file.writestr(f"zip_{zip_code}.csv", csv_data)
            zip_buffer.seek(0)
            st.download_button("Download ZIP Split Files", zip_buffer.getvalue(),
                               "zip_split_address_honw_phone.zip", "application/zip")
            st.success("✅ ZIP split (Address+HoNW+Phone) complete!")

    elif uploaded_file and option != "Select an option":
        df = pd.read_csv(uploaded_file)

        if option == "Company Industry":
            st.write("Processing your file...")
            progress_bar = st.progress(0)
            total_steps = 3

            # Step 1: Check for required column
            required_cols = ['COMPANY_INDUSTRY']
            if not all(col in df.columns for col in required_cols):
                st.error("CSV file must contain the 'COMPANY_INDUSTRY' column.")
                st.stop()

            progress_bar.progress(1 / total_steps)

            # Step 2: Extract unique industries and provide selection interface
            unique_industries = sorted(df['COMPANY_INDUSTRY'].dropna().unique())
            if not unique_industries:
                st.warning("No industries found in the 'COMPANY_INDUSTRY' column.")
                st.stop()

            st.subheader("Select Industries to Filter")
            selected_industries = st.multiselect(
                "Choose one or more industries (start typing to search):",
                options=unique_industries,
                default=None,
                help="Select multiple industries to include in the filtered output."
            )

            if st.button("Filter by Selected Industries"):
                if not selected_industries:
                    st.error("Please select at least one industry to filter.")
                else:
                    # Filter DataFrame based on selected industries
                    filtered_df = df[df['COMPANY_INDUSTRY'].isin(selected_industries)]

                    progress_bar.progress(2 / total_steps)

                    # Step 3: Provide download option
                    st.success("✅ Filtering complete!")
                    st.write(
                        f"Filtered to {len(filtered_df)} rows based on {len(selected_industries)} selected industries.")

                    st.download_button(
                        label="Download Filtered Company Industry Data",
                        data=filtered_df.to_csv(index=False).encode('utf-8'),
                        file_name="filtered_by_company_industry.csv",
                        mime="text/csv"
                    )

                    progress_bar.progress(3 / total_steps)

                    st.info(
                        "The output includes all columns from your original file, filtered to only include rows where "
                        "COMPANY_INDUSTRY matches your selected industries."
                    )
        else:
            if st.button("Process"):
                st.write("Processing your file...")
                progress_bar = st.progress(0)
                total_steps = 6

                # Step 1: Check for required columns
                if option == "Filter by Zip Codes":
                    required_cols = ['PERSONAL_ZIP']
                elif option == "Address + HoNWIncome":
                    required_cols = ['PERSONAL_ADDRESS', 'PERSONAL_CITY']
                elif option == "Address + HoNWIncome & Phone":
                    required_cols = ['PERSONAL_ADDRESS', 'PERSONAL_CITY', 'MOBILE_PHONE', 'DNC']
                elif option == "Sha256":
                    required_cols = ['FIRST_NAME', 'LAST_NAME', 'SHA256_PERSONAL_EMAIL', 'SHA256_BUSINESS_EMAIL']
                elif option == "Full Combined Address":
                    required_cols = ['FIRST_NAME', 'LAST_NAME', 'PERSONAL_ADDRESS', 'PERSONAL_CITY', 'PERSONAL_STATE',
                                     'PERSONAL_ZIP']
                elif option == "Phone & Credit Score":
                    required_cols = ['FIRST_NAME', 'LAST_NAME', 'PERSONAL_ADDRESS', 'PERSONAL_CITY', 'PERSONAL_STATE',
                                     'PERSONAL_ZIP']
                    if 'MOBILE_PHONE' not in df.columns and 'DIRECT_NUMBER' not in df.columns:
                        st.error("CSV file must contain at least one of 'MOBILE_PHONE' or 'DIRECT_NUMBER'.")
                        st.stop()
                elif option == "Split by State":
                    required_cols = ['PERSONAL_ADDRESS', 'PERSONAL_CITY', 'PERSONAL_STATE']
                elif option == "B2B Job Titles Focus":
                    required_cols = ['JOB_TITLE']

                if not all(col in df.columns for col in required_cols):
                    st.error(f"CSV file must contain the following columns: {', '.join(required_cols)}")
                    st.stop()

                progress_bar.progress(1 / total_steps)

                if option == "Filter by Zip Codes":
                    if zip_codes_input:
                        # Ensure PERSONAL_ZIP is string to preserve leading zeros
                        df['PERSONAL_ZIP'] = df['PERSONAL_ZIP'].astype(str)
                        # Create temporary column with first 5 digits, stripping spaces
                        df['PERSONAL_ZIP_5'] = df['PERSONAL_ZIP'].str.strip().str[:5]
                        # Parse input zip codes, taking first 5 characters after stripping
                        zip_codes = [str(zip_code).strip()[:5] for zip_code in zip_codes_input.replace(",", " ").split() if
                                     str(zip_code).strip()]
                        if not zip_codes:
                            st.error("No valid zip codes provided.")
                            st.stop()
                        # Filter the DataFrame
                        filtered_df = df[df['PERSONAL_ZIP_5'].isin(zip_codes)]
                        # Drop the temporary column
                        filtered_df = filtered_df.drop(columns=['PERSONAL_ZIP_5'])
                        # Debugging info to help identify issues
                        st.write("Input Zip Codes (first 5 digits):", zip_codes)
                        st.write("Unique PERSONAL_ZIP_5 in Data:", df['PERSONAL_ZIP_5'].unique())
                        st.write("Number of Matching Rows:", len(filtered_df))
                        if filtered_df.empty:
                            st.warning(
                                "No rows match the provided zip codes. Please check your input against the unique zip codes displayed above or verify the data.")
                        else:
                            st.download_button(
                                label="Download Filtered Data",
                                data=filtered_df.to_csv(index=False).encode('utf-8'),
                                file_name="filtered_by_zip_codes.csv",
                                mime="text/csv"
                            )
                            st.success("✅ Filtering complete!")
                            st.info("Filtered based on the first 5 digits of the provided zip codes.")
                        progress_bar.progress(1.0)
                    else:
                        st.error("Please enter zip codes to filter.")
                        st.stop()
                else:
                    # Step 2: Filter and clean data
                    if option in ["Address + HoNWIncome", "Address + HoNWIncome & Phone", "Full Combined Address",
                                  "Phone & Credit Score", "Split by State"]:
                        df = df[df['PERSONAL_ADDRESS'].notna()]
                        df['PERSONAL_ADDRESS_CLEAN'] = df['PERSONAL_ADDRESS'].apply(clean_address)
                    progress_bar.progress(2 / total_steps)

                    # Step 3: Process data based on option
                    if option == "Address + HoNWIncome" or option == "Address + HoNWIncome & Phone":
                        address_components = ['PERSONAL_ADDRESS_CLEAN']
                        if 'PERSONAL_CITY' in df.columns:
                            address_components.append('PERSONAL_CITY')
                        if 'PERSONAL_STATE' in df.columns:
                            address_components.append('PERSONAL_STATE')
                        df['ADDRESS'] = df[address_components].apply(
                            lambda row: ', '.join([str(x) for x in row if pd.notna(x) and x != '']), axis=1)

                        df['HOMEOWNER'] = df['HOMEOWNER'].fillna('')
                        df['NET_WORTH'] = df['NET_WORTH'].fillna('')
                        df['INCOME_RANGE'] = df['INCOME_RANGE'].fillna('')
                        if option == "Address + HoNWIncome":
                            df['DATA'] = 'Ho ' + df['HOMEOWNER'] + ' | NW ' + df['NET_WORTH'] + ' | Income ' + df[
                                'INCOME_RANGE']
                        else:
                            df['MOBILE_PHONE'] = df['MOBILE_PHONE'].fillna('')
                            df['DNC'] = df['DNC'].fillna('N')
                            df['DATA'] = 'Ho ' + df['HOMEOWNER'] + ' | NW ' + df['NET_WORTH'] + ' | Income ' + df[
                                'INCOME_RANGE'] + \
                                         df.apply(
                                             lambda row: ' | Phone ' + str(row['MOBILE_PHONE']) if row['DNC'] != 'Y' and
                                                                                                   row[
                                                                                                       'MOBILE_PHONE'] != '' else '',
                                             axis=1)
                        output_df = df[['ADDRESS', 'DATA']]
                    elif option == "Sha256":
                        df['SHA256'] = df['SHA256_PERSONAL_EMAIL'].fillna(df['SHA256_BUSINESS_EMAIL'])
                        output_df = df[['FIRST_NAME', 'LAST_NAME', 'SHA256']]
                    elif option == "Full Combined Address":
                        address_clean = df['PERSONAL_ADDRESS_CLEAN'].astype(str)
                        city = df['PERSONAL_CITY'].apply(lambda x: str(x) if pd.notna(x) else '')
                        state = df['PERSONAL_STATE'].apply(lambda x: str(x) if pd.notna(x) else '')
                        zip_code = df['PERSONAL_ZIP'].apply(lambda x: str(x) if pd.notna(x) else '')
                        df['FULL_ADDRESS'] = address_clean + ' ' + city + ', ' + state + ' ' + zip_code
                        if 'MOBILE_PHONE' in df.columns and 'DIRECT_NUMBER' in df.columns:
                            df['PHONE'] = df['MOBILE_PHONE'].fillna(df['DIRECT_NUMBER'])
                        elif 'MOBILE_PHONE' in df.columns:
                            df['PHONE'] = df['MOBILE_PHONE']
                        elif 'DIRECT_NUMBER' in df.columns:
                            df['PHONE'] = df['DIRECT_NUMBER']
                        for col in ['PHONE', 'PERSONAL_EMAIL', 'BUSINESS_EMAIL', 'HOMEOWNER', 'NET_WORTH', 'INCOME_RANGE',
                                    'CHILDREN', 'AGE_RANGE', 'SKIPTRACE_CREDIT_RATING', 'LINKEDIN_URL', 'DNC']:
                            if col in df.columns:
                                df[col] = df[col].fillna('')
                        output_df = df[
                            ['FIRST_NAME', 'LAST_NAME', 'PHONE', 'FULL_ADDRESS', 'PERSONAL_EMAIL', 'BUSINESS_EMAIL',
                             'HOMEOWNER', 'NET_WORTH', 'INCOME_RANGE', 'CHILDREN', 'AGE_RANGE', 'SKIPTRACE_CREDIT_RATING',
                             'LINKEDIN_URL', 'DNC']]
                    elif option == "Phone & Credit Score":
                        if 'MOBILE_PHONE' in df.columns and 'DIRECT_NUMBER' in df.columns:
                            df['PHONE'] = df['MOBILE_PHONE'].fillna(df['DIRECT_NUMBER'])
                        elif 'MOBILE_PHONE' in df.columns:
                            df['PHONE'] = df['MOBILE_PHONE']
                        elif 'DIRECT_NUMBER' in df.columns:
                            df['PHONE'] = df['DIRECT_NUMBER']
                        for col in ['PERSONAL_STATE', 'PERSONAL_ZIP', 'PERSONAL_EMAIL', 'LINKEDIN_URL',
                                    'SKIPTRACE_CREDIT_RATING', 'DNC']:
                            if col in df.columns:
                                df[col] = df[col].fillna('')
                        output_df = df[['FIRST_NAME', 'LAST_NAME', 'PHONE', 'PERSONAL_ADDRESS_CLEAN', 'PERSONAL_CITY',
                                        'PERSONAL_STATE', 'PERSONAL_ZIP', 'PERSONAL_EMAIL', 'LINKEDIN_URL',
                                        'SKIPTRACE_CREDIT_RATING', 'DNC']]
                    elif option == "Split by State":
                        output_df = df
                    elif option == "B2B Job Titles Focus":
                        b2b_job_titles_columns = [
                            'FIRST_NAME', 'LAST_NAME', 'JOB_TITLE', 'DEPARTMENT', 'SENIORITY_LEVEL',
                            'JOB_TITLE_LAST_UPDATED',
                            'COMPANY_INDUSTRY', 'BUSINESS_EMAIL', 'LINKEDIN_URL', 'AGE_RANGE', 'GENDER',
                            'SKIPTRACE_B2B_COMPANY_NAME',
                            'SKIPTRACE_B2B_MATCH_SCORE', 'SKIPTRACE_B2B_ADDRESS', 'SKIPTRACE_B2B_PHONE',
                            'SKIPTRACE_B2B_SOURCE',
                            'SKIPTRACE_B2B_WEBSITE', 'COMPANY_INDUSTRY2', 'COMPANY_NAME', 'COMPANY_ADDRESS',
                            'COMPANY_DESCRIPTION',
                            'COMPANY_DOMAIN', 'COMPANY_EMPLOYEE_COUNT', 'COMPANY_LINKEDIN_URL', 'COMPANY_PHONE',
                            'COMPANY_REVENUE',
                            'COMPANY_SIC', 'COMPANY_NAICS', 'COMPANY_CITY', 'COMPANY_STATE', 'COMPANY_ZIP',
                            'COMPANY_LAST_UPDATED',
                            'PROFESSIONAL_ADDRESS', 'PROFESSIONAL_ADDRESS_2', 'PROFESSIONAL_CITY', 'PROFESSIONAL_STATE',
                            'PROFESSIONAL_ZIP', 'PROFESSIONAL_ZIP4', 'DNC', 'DIRECT_NUMBER', 'MOBILE_PHONE',
                            'PERSONAL_PHONE',
                            'PERSONAL_CITY', 'PERSONAL_STATE', 'PERSONAL_ZIP'
                        ]
                        available_columns = [col for col in b2b_job_titles_columns if col in df.columns]
                        output_df = df[available_columns]

                    progress_bar.progress(3 / total_steps)

                    # Step 4: Split files
                    def split_dataframe(df, max_rows=2000):
                        return [df[i:i + max_rows] for i in range(0, len(df), max_rows)]


                    output_files = []
                    if option in ["Address + HoNWIncome", "Address + HoNWIncome & Phone"]:
                        if len(output_df) > 2000:
                            split_dfs = split_dataframe(output_df)
                            for i, split_df in enumerate(split_dfs):
                                output_files.append((f"output_{option.lower().replace(' ', '_')}_part_{i + 1}", split_df))
                        else:
                            output_files.append((f"output_{option.lower().replace(' ', '_')}", output_df))
                    elif option == "Split by State":
                        for state, group in output_df.groupby('PERSONAL_STATE'):
                            state_df = group
                            output_files.append((f"output_split_by_state_{state}", state_df))
                    else:
                        output_files.append((f"output_{option.lower().replace(' ', '_')}", output_df))

                    progress_bar.progress(4 / total_steps)

                    # Step 5: Provide download options
                    st.success("✅ Processing complete!")

                    if option in ["Address + HoNWIncome", "Address + HoNWIncome & Phone", "Split by State"] and len(
                            output_files) > 1:
                        zip_buffer = io.BytesIO()
                        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
                            for file_name, df_part in output_files:
                                csv_data = df_part.to_csv(index=False).encode('utf-8')
                                zip_file.writestr(f"{file_name}.csv", csv_data)
                        zip_buffer.seek(0)
                        st.download_button(
                            label="Download All Files as ZIP",
                            data=zip_buffer.getvalue(),
                            file_name="all_files.zip",
                            mime="application/zip",
                            key="download_all_zip",
                            help="Click to download all split files as a ZIP",
                            type="primary"
                        )

                    for file_name, df_part in output_files:
                        if option != "B2B Job Titles Focus":
                            st.download_button(
                                label=f"Download {file_name}.csv",
                                data=df_part.to_csv(index=False).encode('utf-8'),
                                file_name=f"{file_name}.csv",
                                mime="text/csv"
                            )

                    if option == "B2B Job Titles Focus":
                        file_name, df_part = output_files[0]
                        excel_buffer = io.BytesIO()
                        with pd.ExcelWriter(excel_buffer, engine='openpyxl') as writer:
                            df_part.to_excel(writer, index=False, sheet_name='B2B Job Titles')
                        excel_buffer.seek(0)
                        st.download_button(
                            label="Download output_b2b_job_titles_focus.xlsx",
                            data=excel_buffer.getvalue(),
                            file_name="output_b2b_job_titles_focus.xlsx",
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                        )

                    progress_bar.progress(5 / total_steps)

                    # Step 6: Display instructions
                    st.info(
                        f"**Note:** Your file has been processed using the '{option}' option. The addresses have been cleaned "
                        f"for address-related options. 'Address + HoNWIncome' and 'Address + HoNWIncome & Phone' split files "
                        f"at 2000 rows with individual downloads and a ZIP option. 'Split by State' creates one file per state "
                        f"with a ZIP if multiple states. 'B2B Job Titles Focus' outputs a single .xlsx file."
                    )

                    if option in ["Address + HoNWIncome", "Address + HoNWIncome & Phone"]:
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
                    elif option == "Split by State":
                        st.markdown("""
                        ### How to Import into Google My Maps:
                        1. Go to [Google My Maps](https://www.google.com/mymaps).
                        2. Click **Create a new map**.
                        3. In the new map, click **Import** under the layer section.
                        4. Upload the downloaded CSV file(s) for each state (or extract from ZIP).
                        5. Set the following:
                           - **Placemarker Pins**: Select the `PERSONAL_ADDRESS_CLEAN` column or combine with `PERSONAL_CITY` and `PERSONAL_STATE`.
                           - **Placemarker Name (Title)**: Choose any relevant column (e.g., `FIRST_NAME`, `LAST_NAME`).
                        6. Dismiss any locations that result in an error during import.
                        7. Zoom out and manually delete any pins that are significantly distant from the main cluster.
                        """)
                    elif option == "B2B Job Titles Focus":
                        st.markdown("""
                        ### Notes for Usage:
                        - The output is a single Excel file (.xlsx) containing B2B job title data and related professional/company details.
                        - Open in Excel or similar tools for analysis of job roles, company info, and contact details.
                        """)

                    progress_bar.progress(6 / total_steps)

    elif option == "Select an option":
        st.warning("Please select a cleaning option before processing.")