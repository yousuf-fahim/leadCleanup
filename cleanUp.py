import pandas as pd
import usaddress
import re

# Define comprehensive abbreviation dictionaries
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
                elif key == 'StreetName':
                    # Check for street type abbreviations within StreetName
                    words = value.split()
                    cleaned_words = []
                    for word in words:
                        cleaned_word = street_type_abbr.get(word, word)
                        cleaned_words.append(cleaned_word)
                    cleaned_components.append(' '.join(cleaned_words))
                else:
                    cleaned_components.append(value)
            cleaned_address = ' '.join(cleaned_components)

            # Post-processing: Replace any remaining abbreviations in the final string
            for abbr, full in directional_abbr.items():
                cleaned_address = re.sub(r'\b' + re.escape(abbr) + r'\b', full, cleaned_address)
            for abbr, full in street_type_abbr.items():
                cleaned_address = re.sub(r'\b' + re.escape(abbr) + r'\b', full, cleaned_address)
            for abbr, full in unit_abbr.items():
                cleaned_address = re.sub(r'\b' + re.escape(abbr) + r'\b', full, cleaned_address)

            return cleaned_address
        elif address_type == 'PO Box':
            return 'PO Box ' + parsed['USPSBoxID']
        else:
            return address  # Return unchanged if not a street address or PO Box
    except usaddress.RepeatedLabelError:
        return address  # Return unchanged if parsing fails

# Load the input CSV
input_file = 'input.csv'  # Replace with your input file path
df = pd.read_csv(input_file)

# Filter out rows with empty PERSONAL_ADDRESS
df = df[df['PERSONAL_ADDRESS'].notna()]

# Clean the PERSONAL_ADDRESS column
df['PERSONAL_ADDRESS_CLEAN'] = df['PERSONAL_ADDRESS'].apply(clean_address)

# Create the ADDRESS column
df['ADDRESS'] = df['PERSONAL_ADDRESS_CLEAN'] + ' ' + df['PERSONAL_CITY']

# Handle missing values in HOMEOWNER, NET_WORTH, INCOME_RANGE
df['HOMEOWNER'] = df['HOMEOWNER'].fillna('')
df['NET_WORTH'] = df['NET_WORTH'].fillna('')
df['INCOME_RANGE'] = df['INCOME_RANGE'].fillna('')

# Create the DATA column
df['DATA'] = 'Ho ' + df['HOMEOWNER'] + ' | NW ' + df['NET_WORTH'] + ' | Income ' + df['INCOME_RANGE']

# Select only the required columns
output_df = df[['ADDRESS', 'DATA']]

# Save to output CSV
output_file = 'output.csv'  # Replace with your desired output file path
output_df.to_csv(output_file, index=False)

print(f"Processing complete. Output saved to {output_file}")