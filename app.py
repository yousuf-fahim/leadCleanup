import streamlit as st
import pandas as pd
import usaddress
import re

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
st.title("📍 Address Cleaner")

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

        # Instructions for My Maps
        st.markdown("""
        ### How to Import into Google My Maps:
        1. Go to [Google My Maps](https://www.google.com/mymaps).
        2. Click **Create a new map**.
        3. In the new map, click **Import** under the layer section.
        4. Upload the downloaded `output.csv` file.
        5. Set the following:
           - **Placemarker Pins**: Select the `ADDRESS` column.
           - **Placemarker Name (Title)**: Select the `DATA` column.
        6. Dismiss any locations that result in an error during import.
        7. Zoom out and manually delete any pins that are significantly distant from the main cluster (e.g., if most pins are in Miami, Florida, remove pins more than 50 miles / 80 km away).
        """)