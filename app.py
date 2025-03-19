import streamlit as st
import pandas as pd
import usaddress
import io
import zipfile

# Define abbreviation dictionaries
directional_abbr = {
    'N': 'North', 'S': 'South', 'E': 'East', 'W': 'West',
    'NE': 'Northeast', 'NW': 'Northwest', 'SE': 'Southeast', 'SW': 'Southwest',
    'NORTH': 'North', 'SOUTH': 'South', 'EAST': 'East', 'WEST': 'West',
    'NORTHEAST': 'Northeast', 'NORTHWEST': 'Northwest', 'SOUTHEAST': 'Southeast', 'SOUTHWEST': 'Southwest'
}

street_type_abbr = {
    'St': 'Street', 'Ave': 'Avenue', 'Blvd': 'Boulevard', 'Rd': 'Road',
    'Ln': 'Lane', 'Dr': 'Drive', 'Ct': 'Court', 'Pl': 'Place',
    'Sq': 'Square', 'Ter': 'Terrace', 'Cir': 'Circle', 'Pkwy': 'Parkway',
    'Trl': 'Trail', 'Trce': 'Trace', 'Hwy': 'Highway', 'Ctr': 'Center',
    'Spg': 'Spring', 'Lk': 'Lake', 'Aly': 'Alley', 'Bnd': 'Bend', 'Brg': 'Bridge',
    'Byu': 'Bayou', 'Clf': 'Cliff', 'Cor': 'Corner', 'Cv': 'Cove', 'Crk': 'Creek',
    'Xing': 'Crossing', 'Gdn': 'Garden', 'Gln': 'Glen', 'Grn': 'Green',
    'Hbr': 'Harbor', 'Holw': 'Hollow', 'Is': 'Island', 'Jct': 'Junction',
    'Knl': 'Knoll', 'Mdws': 'Meadows', 'Mtn': 'Mountain', 'Pass': 'Pass',
    'Pt': 'Point', 'Rnch': 'Ranch', 'Shrs': 'Shores', 'Sta': 'Station',
    'Vly': 'Valley', 'Vw': 'View', 'Wlk': 'Walk',
    'Anx': 'Annex', 'Arc': 'Arcade', 'Av': 'Avenue', 'Bch': 'Beach',
    'Bg': 'Burg', 'Bgs': 'Burgs', 'Blf': 'Bluff', 'Blfs': 'Bluffs',
    'Bot': 'Bottom', 'Br': 'Branch', 'Brk': 'Brook', 'Brks': 'Brooks',
    'Btw': 'Between', 'Cmn': 'Common', 'Cmp': 'Camp', 'Cnyn': 'Canyon',
    'Cpe': 'Cape', 'Cswy': 'Causeway', 'Clb': 'Club', 'Con': 'Corner',
    'Cors': 'Corners', 'Cp': 'Camp', 'Cres': 'Crescent', 'Crst': 'Crest',
    'Xrd': 'Crossroad', 'Ext': 'Extension', 'Falls': 'Falls', 'Frk': 'Fork',
    'Frks': 'Forks', 'Ft': 'Fort', 'Fwy': 'Freeway', 'Gdns': 'Gardens',
    'Gtway': 'Gateway', 'Hghts': 'Heights', 'Hvn': 'Haven', 'Hd': 'Head',
    'Hlls': 'Hills', 'Inlt': 'Inlet', 'Jcts': 'Junctions', 'Ky': 'Key',
    'Kys': 'Keys', 'Lndg': 'Landing', 'Lgt': 'Light', 'Lgts': 'Lights',
    'Lf': 'Loaf', 'Mnr': 'Manor', 'Mls': 'Mills', 'Mssn': 'Mission',
    'Mt': 'Mount', 'Nck': 'Neck', 'Orch': 'Orchard', 'Oval': 'Oval',
    'Prk': 'Park', 'Pkwys': 'Parkways', 'Pln': 'Plain', 'Plz': 'Plaza',
    'Prt': 'Port', 'Pr': 'Prairie', 'Rad': 'Radial', 'Rdg': 'Ridge',
    'Riv': 'River', 'Rdge': 'Ridge', 'Run': 'Run', 'Shl': 'Shoal',
    'Shls': 'Shoals', 'Skwy': 'Skyway', 'Spgs': 'Springs', 'Spur': 'Spur',
    'Strm': 'Stream', 'Stm': 'Stream', 'Trfy': 'Terrace', 'Trwy': 'Throughway',
    'Tpke': 'Turnpike', 'Un': 'Union', 'Vlg': 'Village', 'Vis': 'Vista',
    'Way': 'Way', 'Expy': 'Expressway', 'Frwy': 'Freeway', 'Tunl': 'Tunnel'
}

unit_abbr = {
    'Apt': 'Apartment', 'Ste': 'Suite', 'Bldg': 'Building',
    'Unit': 'Unit', 'Rm': 'Room', 'Fl': 'Floor', 'Dep': 'Department',
    'Ofc': 'Office', 'Sp': 'Space', 'Lot': 'Lot', 'Trlr': 'Trailer',
    'Hangar': 'Hangar', 'Slip': 'Slip', 'Pier': 'Pier', 'Dock': 'Dock'
}

def clean_address(address):
    """Parse and expand abbreviations in an address with fallback for malformed addresses."""
    try:
        parsed, address_type = usaddress.tag(address)
        if address_type == 'Street Address':
            cleaned_components = []
            for key, value in parsed.items():
                if key in ['StreetNamePreDirectional', 'StreetNamePostDirectional']:
                    cleaned_components.append(directional_abbr.get(value.upper(), value))
                elif key == 'StreetNamePostType':
                    cleaned_components.append(street_type_abbr.get(value.upper(), value))
                elif key == 'OccupancyType':
                    cleaned_components.append(unit_abbr.get(value.upper(), value))
                else:
                    cleaned_components.append(value)
            return ' '.join(cleaned_components)
        elif address_type == 'PO Box':
            return 'PO Box ' + parsed['USPSBoxID']
        else:
            words = address.split()
            cleaned = [directional_abbr.get(word.upper(), street_type_abbr.get(word.upper(), unit_abbr.get(word.upper(), word))) for word in words]
            return ' '.join(cleaned)
    except usaddress.RepeatedLabelError:
        words = address.split()
        cleaned = [directional_abbr.get(word.upper(), street_type_abbr.get(word.upper(), unit_abbr.get(word.upper(), word))) for word in words]
        return ' '.join(cleaned)

# Streamlit UI
st.title("📍 Address Cleaner")

st.markdown(
    "[📥 Download Sample CSV](https://drive.google.com/file/d/19CdaLPNq7SUY1ROx0RgLdFD9gQI9JrSh/view?usp=sharing)",
    unsafe_allow_html=True)

uploaded_file = st.file_uploader("Upload your CSV file (max 200MB)", type=["csv"], accept_multiple_files=False,
                                 help="Maximum file size: 200MB (depending on deployment environment)")

options = [
    "Select an option",
    "Address + HoNWIncome",
    "Address + HoNWIncome & Phone",
    "Sha256",
    "Full Combined Address",
    "Phone & Credit Score",
    "Split by State"
]
option = st.selectbox("Select Cleaning Option", options, index=0)

descriptions = {
    "Address + HoNWIncome": "Combines cleaned address with homeowner status, net worth, and income range.",
    "Address + HoNWIncome & Phone": "Adds phone number to the combined data if not marked as Do Not Call (DNC).",
    "Sha256": "Provides names with hashed email data, preferring personal email hash.",
    "Full Combined Address": "Generates a comprehensive dataset with full address and additional metadata.",
    "Phone & Credit Score": "Focuses on phone numbers and credit scores with address details.",
    "Split by State": "Splits the dataset into one file per state based on the PERSONAL_STATE column."
}

if option != "Select an option":
    st.info(descriptions[option])

if uploaded_file and option != "Select an option" and st.button("Process"):
    df = pd.read_csv(uploaded_file)

    st.write("Processing your file...")
    progress_bar = st.progress(0)
    total_steps = 6

    # Step 1: Check for required columns
    if option == "Address + HoNWIncome":
        required_cols = ['PERSONAL_ADDRESS', 'PERSONAL_CITY']
    elif option == "Address + HoNWIncome & Phone":
        required_cols = ['PERSONAL_ADDRESS', 'PERSONAL_CITY', 'MOBILE_PHONE', 'DNC']
    elif option == "Sha256":
        required_cols = ['FIRST_NAME', 'LAST_NAME', 'SHA256_PERSONAL_EMAIL', 'SHA256_BUSINESS_EMAIL']
    elif option == "Full Combined Address":
        required_cols = ['FIRST_NAME', 'LAST_NAME', 'PERSONAL_ADDRESS', 'PERSONAL_CITY', 'PERSONAL_STATE', 'PERSONAL_ZIP']
    elif option == "Phone & Credit Score":
        required_cols = ['FIRST_NAME', 'LAST_NAME', 'PERSONAL_ADDRESS', 'PERSONAL_CITY', 'PERSONAL_STATE', 'PERSONAL_ZIP']
        if 'MOBILE_PHONE' not in df.columns and 'DIRECT_NUMBER' not in df.columns:
            st.error("CSV file must contain at least one of 'MOBILE_PHONE' or 'DIRECT_NUMBER'.")
            st.stop()
    elif option == "Split by State":
        required_cols = ['PERSONAL_ADDRESS', 'PERSONAL_CITY', 'PERSONAL_STATE']

    if not all(col in df.columns for col in required_cols):
        st.error(f"CSV file must contain the following columns: {', '.join(required_cols)}")
        st.stop()

    progress_bar.progress(1 / total_steps)

    # Step 2: Filter and clean data
    if option in ["Address + HoNWIncome", "Address + HoNWIncome & Phone", "Full Combined Address",
                  "Phone & Credit Score", "Split by State"]:
        df = df[df['PERSONAL_ADDRESS'].notna()]
        df['PERSONAL_ADDRESS_CLEAN'] = df['PERSONAL_ADDRESS'].apply(clean_address)

    progress_bar.progress(2 / total_steps)

    # Step 3: Process data based on option
    if option == "Address + HoNWIncome":
        df['ADDRESS'] = df['PERSONAL_ADDRESS_CLEAN'] + ' ' + df['PERSONAL_CITY']
        df['HOMEOWNER'] = df['HOMEOWNER'].fillna('')
        df['NET_WORTH'] = df['NET_WORTH'].fillna('')
        df['INCOME_RANGE'] = df['INCOME_RANGE'].fillna('')
        df['DATA'] = 'Ho ' + df['HOMEOWNER'] + ' | NW ' + df['NET_WORTH'] + ' | Income ' + df['INCOME_RANGE']
        output_df = df[['ADDRESS', 'DATA']]
    elif option == "Address + HoNWIncome & Phone":
        df['ADDRESS'] = df['PERSONAL_ADDRESS_CLEAN'] + ' ' + df['PERSONAL_CITY']
        df['HOMEOWNER'] = df['HOMEOWNER'].fillna('')
        df['NET_WORTH'] = df['NET_WORTH'].fillna('')
        df['INCOME_RANGE'] = df['INCOME_RANGE'].fillna('')
        df['MOBILE_PHONE'] = df['MOBILE_PHONE'].fillna('')
        df['DNC'] = df['DNC'].fillna('N')
        df['DATA'] = 'Ho ' + df['HOMEOWNER'] + ' | NW ' + df['NET_WORTH'] + ' | Income ' + df['INCOME_RANGE'] + \
                     df.apply(lambda row: ' | Phone ' + str(row['MOBILE_PHONE']) if row['DNC'] != 'Y' and row[
                         'MOBILE_PHONE'] != '' else '', axis=1)
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
        output_df = df[['FIRST_NAME', 'LAST_NAME', 'PHONE', 'FULL_ADDRESS', 'PERSONAL_EMAIL', 'BUSINESS_EMAIL',
                        'HOMEOWNER', 'NET_WORTH', 'INCOME_RANGE', 'CHILDREN', 'AGE_RANGE', 'SKIPTRACE_CREDIT_RATING',
                        'LINKEDIN_URL', 'DNC']]
    elif option == "Phone & Credit Score":
        if 'MOBILE_PHONE' in df.columns and 'DIRECT_NUMBER' in df.columns:
            df['PHONE'] = df['MOBILE_PHONE'].fillna(df['DIRECT_NUMBER'])
        elif 'MOBILE_PHONE' in df.columns:
            df['PHONE'] = df['MOBILE_PHONE']
        elif 'DIRECT_NUMBER' in df.columns:
            df['PHONE'] = df['DIRECT_NUMBER']
        for col in ['PERSONAL_STATE', 'PERSONAL_ZIP', 'PERSONAL_EMAIL', 'LINKEDIN_URL', 'SKIPTRACE_CREDIT_RATING',
                    'DNC']:
            if col in df.columns:
                df[col] = df[col].fillna('')
        output_df = df[['FIRST_NAME', 'LAST_NAME', 'PHONE', 'PERSONAL_ADDRESS_CLEAN', 'PERSONAL_CITY',
                        'PERSONAL_STATE', 'PERSONAL_ZIP', 'PERSONAL_EMAIL', 'LINKEDIN_URL', 'SKIPTRACE_CREDIT_RATING',
                        'DNC']]
    elif option == "Split by State":
        output_df = df  # Keep all original columns

    progress_bar.progress(3 / total_steps)

    # Step 4: Split files only for first two options at 2000 entries
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
            state_df = group  # Retain all columns from the original DataFrame
            output_files.append((f"output_split_by_state_{state}", state_df))  # No 2000-row split
    else:
        # No splitting for Sha256, Full Combined Address, Phone & Credit Score
        output_files.append((f"output_{option.lower().replace(' ', '_')}", output_df))

    progress_bar.progress(4 / total_steps)

    # Step 5: Provide download options
    st.success("✅ Processing complete!")

    if len(output_files) > 1:
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            for file_name, df_part in output_files:
                csv_data = df_part.to_csv(index=False).encode('utf-8')
                zip_file.writestr(f"{file_name}.csv", csv_data)
        zip_buffer.seek(0)

        st.markdown(
            """
            <style>
            .big-button {
                background-color: #4CAF50;
                color: white;
                padding: 15px 32px;
                text-align: center;
                text-decoration: none;
                display: inline-block;
                font-size: 16px;
                margin: 4px 2px;
                cursor: pointer;
                border: none;
                border-radius: 12px;
            }
            </style>
            """,
            unsafe_allow_html=True
        )

        st.download_button(
            label="Download All Files as ZIP",
            data=zip_buffer.getvalue(),
            file_name="all_files.zip",
            mime="application/zip",
            key="download_all_zip",
            help="Click to download all files as a ZIP",
            type="primary"
        )

    for file_name, df_part in output_files:
        st.download_button(
            label=f"Download {file_name}.csv",
            data=df_part.to_csv(index=False).encode('utf-8'),
            file_name=f"{file_name}.csv",
            mime="text/csv"
        )

    progress_bar.progress(5 / total_steps)

    # Step 6: Display note and instructions
    st.info(
        f"**Note:** Your file has been processed using the '{option}' option. The addresses have been cleaned, "
        f"and relevant data has been combined. Files are split for 'Address + HoNWIncome' and "
        f"'Address + HoNWIncome & Phone' if they exceed 2000 rows. 'Split by State' creates one file per state."
    )

    if option in ["Address + HoNWIncome", "Address + HoNWIncome & Phone"]:
        st.markdown("""
        ### How to Import into Google My Maps:
        1. Go to [Google My Maps](https://www.google.com/mymaps).
        2. Click **Create a new map**.
        3. In the new map, click **Import** under the layer section.
        4. Upload the downloaded CSV file(s).
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

    progress_bar.progress(6 / total_steps)

elif option == "Select an option":
    st.warning("Please select a cleaning option before processing.")