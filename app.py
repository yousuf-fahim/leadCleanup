import streamlit as st
import pandas as pd
import usaddress
import re

# Define abbreviation dictionaries
directional_abbr = {
    'N': 'North', 'S': 'South', 'E': 'East', 'W': 'West',
    'NE': 'Northeast', 'NW': 'Northwest', 'SE': 'Southeast', 'SW': 'Southwest'
}

street_type_abbr = {
    'St': 'Street', 'Ave': 'Avenue', 'Blvd': 'Boulevard', 'Rd': 'Road',
    'Ln': 'Lane', 'Dr': 'Drive', 'Ct': 'Court', 'Pl': 'Place'
}

unit_abbr = {
    'Apt': 'Apartment', 'Ste': 'Suite', 'Bldg': 'Building',
    'Unit': 'Unit', 'Rm': 'Room', 'Fl': 'Floor'
}

def clean_address(address):
    """Parse and expand abbreviations in an address."""
    try:
        parsed, address_type = usaddress.tag(address)
        if address_type == 'Street Address':
            cleaned_components = []
            for key, value in parsed.items():
                if key in ['StreetNamePreDirectional', 'StreetNamePostDirectional'] and value in directional_abbr:
                    cleaned_components.append(directional_abbr[value])
                elif key == 'StreetNamePostType' and value in street_type_abbr:
                    cleaned_components.append(street_type_abbr[value])
                elif key == 'OccupancyType' and value in unit_abbr:
                    cleaned_components.append(unit_abbr[value])
                else:
                    cleaned_components.append(value)
            return ' '.join(cleaned_components)
        elif address_type == 'PO Box':
            return 'PO Box ' + parsed['USPSBoxID']
        else:
            return address
    except usaddress.RepeatedLabelError:
        return address

# Streamlit UI
st.title("📍 Address Cleaner for Leads")

# Add hyperlink for sample CSV download
st.markdown("[📥 Download Sample CSV](https://drive.google.com/file/d/19CdaLPNq7SUY1ROx0RgLdFD9gQI9JrSh/view?usp=sharing)", unsafe_allow_html=True)

uploaded_file = st.file_uploader("Upload your CSV file", type=["csv"])

if uploaded_file:
    df = pd.read_csv(uploaded_file)

    if "PERSONAL_ADDRESS" not in df.columns or "PERSONAL_CITY" not in df.columns:
        st.error("CSV file must contain 'PERSONAL_ADDRESS' and 'PERSONAL_CITY' columns.")
    else:
        df = df[df['PERSONAL_ADDRESS'].notna()]
        df['PERSONAL_ADDRESS_CLEAN'] = df['PERSONAL_ADDRESS'].apply(clean_address)
        df['ADDRESS'] = df['PERSONAL_ADDRESS_CLEAN'] + ' ' + df['PERSONAL_CITY']
        df['HOMEOWNER'] = df['HOMEOWNER'].fillna('')
        df['NET_WORTH'] = df['NET_WORTH'].fillna('')
        df['INCOME_RANGE'] = df['INCOME_RANGE'].fillna('')
        df['DATA'] = 'Ho ' + df['HOMEOWNER'] + ' | NW ' + df['NET_WORTH'] + ' | Income ' + df['INCOME_RANGE']
        output_df = df[['ADDRESS', 'DATA']]

        st.success("✅ Processing complete!")

        # Download button
        st.download_button(
            label="Download Processed CSV",
            data=output_df.to_csv(index=False).encode('utf-8'),
            file_name="output.csv",
            mime="text/csv"
        )
