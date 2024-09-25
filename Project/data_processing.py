import pandas as pd

def ladda_data(file_path):
    """
    Load Excel data and return a dictionary of dataframes.
    """
    # Load the Excel file from the given file path
    excel_data = pd.ExcelFile(file_path)
    
    # Parse the sheets into separate dataframes
    data = {
        'brukare': excel_data.parse('Individer, brukare', header=1),
        'medarbetare': excel_data.parse('Medarbetare', header=2)
    }

    return data

def rensa_brukar_data(brukare_df):
    """
    Cleans brukare data by filtering rows and converting boolean columns.
    """
    brukare_df.rename(columns={'Unnamed: 0': 'Individ'}, inplace=True)
    brukare_df = brukare_df.dropna(subset=['Individ']).copy()
    brukare_df.fillna('-', inplace=True)
    brukare_df['Kräver körkort'] = brukare_df['Kräver körkort'].apply(lambda x: x == 'Ja')
    brukare_df['Röker'] = brukare_df['Röker'].apply(lambda x: x == 'Ja')
    brukare_df['Har hund'] = brukare_df['Har hund'].apply(lambda x: x == 'Ja')
    brukare_df['Har katt'] = brukare_df['Har katt'].apply(lambda x: x == 'Ja')
    brukare_df['Kräver >18'] = brukare_df['Kräver >18'].apply(lambda x: x == 'Ja')
    return brukare_df

def rensa_medarb_data(medarbetare_df):
    """
    Cleans medarbetare data by converting binary columns to boolean values.
    """
    medarbetare_df.rename(columns={'Unnamed: 0': 'Medarbetare'}, inplace=True)
    medarbetare_df.fillna('-', inplace=True)
    for column in medarbetare_df.columns[1:]:
        medarbetare_df[column] = medarbetare_df[column].apply(lambda x: x == 'Ja')
    return medarbetare_df

def read_addresses(file_path):
    """
    Reads addresses and coordinates from a file and returns them as a list of tuples.
    :param file_path: Path to the address file
    :return: List of tuples containing address and coordinates (latitude, longitude)
    """
    addresses = []
    with open(file_path, 'r') as file:
        for line in file:
            try:
                # Extract the address and coordinates by splitting the line based on the comma that separates address and coordinates
                parts = line.split(", ", 1)  # Split only on the first comma
                address_part = parts[0].split('. ', 1)[1]  # Split by '. ' to remove the initial numbering
                coordinates = eval(parts[1].strip())  # Evaluate the string to a tuple (64.754, 21.046)

                # Check if the parsed coordinates are valid
                if isinstance(coordinates, tuple) and len(coordinates) == 2:
                    addresses.append((address_part, coordinates))
                else:
                    print(f"Invalid coordinates format for address: {address_part}")
            except (SyntaxError, IndexError, NameError, TypeError) as e:
                print(f"Error parsing coordinates for line: {line.strip()}, Error: {e}")
    return addresses


def assign_addresses_to_brukare(brukare_df, addresses):
    """
    Assigns addresses and coordinates to brukare.
    :param brukare_df: DataFrame of brukare
    :param addresses: List of tuples containing addresses and coordinates
    :return: Updated brukare DataFrame with addresses
    """
    if len(addresses) < len(brukare_df):
        raise ValueError("Not enough addresses for all brukare. Please add more addresses.")
    
    for i, (address, coordinates) in enumerate(addresses):
        if i < len(brukare_df):
            brukare_df.at[i, 'Address'] = address
            brukare_df.at[i, 'Latitude'] = coordinates[0]
            brukare_df.at[i, 'Longitude'] = coordinates[1]
    
    return brukare_df

