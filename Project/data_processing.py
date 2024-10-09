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
    Cleans brukare data by filtering rows, converting boolean columns, and setting up constraints.
    """
    brukare_df.rename(columns={'Unnamed: 0': 'Individ'}, inplace=True)
    brukare_df = brukare_df.dropna(subset=['Individ']).copy()
    brukare_df.fillna('-', inplace=True)
    
    # Convert relevant columns to boolean, only if the column exists
    if 'Kräver körkort' in brukare_df.columns:
        brukare_df['Kräver körkort'] = brukare_df['Kräver körkort'].apply(lambda x: x == 'Ja')
    if 'Röker' in brukare_df.columns:
        brukare_df['Röker'] = brukare_df['Röker'].apply(lambda x: x == 'Ja')
    if 'Har hund' in brukare_df.columns:
        brukare_df['Har hund'] = brukare_df['Har hund'].apply(lambda x: x == 'Ja')
    if 'Har katt' in brukare_df.columns:
        brukare_df['Har katt'] = brukare_df['Har katt'].apply(lambda x: x == 'Ja')
    if 'Kräver >18' in brukare_df.columns:
        brukare_df['Kräver >18'] = brukare_df['Kräver >18'].apply(lambda x: x == 'Ja')
    if 'Kräver man' in brukare_df.columns:
        brukare_df['Kräver man'] = brukare_df['Kräver man'].apply(lambda x: 'Ja' in x)
    if 'Kräver kvinna' in brukare_df.columns:
        brukare_df['Kräver kvinna'] = brukare_df['Kräver kvinna'].apply(lambda x: 'Ja' in x)
    if 'Behöver läkemedel' in brukare_df.columns:
        brukare_df['Behöver läkemedel'] = brukare_df['Behöver läkemedel'].apply(lambda x: x == 'Ja')
    if 'Behöver insulin' in brukare_df.columns:
        brukare_df['Behöver insulin'] = brukare_df['Behöver insulin'].apply(lambda x: x == 'Ja')
    if 'Har stomi' in brukare_df.columns:
        brukare_df['Har stomi'] = brukare_df['Har stomi'].apply(lambda x: x == 'Ja')
    if 'Dubbelbemanning' in brukare_df.columns:
        brukare_df['Dubbelbemanning'] = brukare_df['Dubbelbemanning'].apply(lambda x: x == 'Ja')
    if 'Dusch' in brukare_df.columns:
        brukare_df['Dusch'] = brukare_df['Dusch'].apply(lambda x: 'Ja' in x)
    if 'Aktivering' in brukare_df.columns:
        brukare_df['Aktivering'] = brukare_df['Aktivering'].apply(lambda x: 'Ja' in x)
    
    # Add constraints as a combined string to be used in optimization
    brukare_df['Constraints'] = brukare_df.apply(lambda row: ','.join(filter(None, [
        'license' if row.get('Kräver körkort', False) else '',
        'smoker' if row.get('Röker', False) else '',
        'dog' if row.get('Har hund', False) else '',
        'cat' if row.get('Har katt', False) else '',
        '>18' if row.get('Kräver >18', False) else '',
        'man' if row.get('Kräver man', False) else '',
        'woman' if row.get('Kräver kvinna', False) else '',
        'medication' if row.get('Behöver läkemedel', False) else '',
        'insulin' if row.get('Behöver insulin', False) else '',
        'stoma' if row.get('Har stomi', False) else '',
        'double_staffing' if row.get('Dubbelbemanning', False) else '',
        'shower' if row.get('Dusch', False) else '',
        'activation' if row.get('Aktivering', False) else ''
    ])).strip(','), axis=1)

    return brukare_df


def rensa_medarb_data(medarbetare_df):
    """
    Cleans medarbetare data by converting binary columns to boolean values and creating capabilities.
    """
    medarbetare_df.rename(columns={'Unnamed: 0': 'Medarbetare'}, inplace=True)
    medarbetare_df.fillna('-', inplace=True)

    # Convert columns to boolean where applicable
    medarbetare_df['Tål hund'] = medarbetare_df['Tål hund'].apply(lambda x: x == 'Ja')
    medarbetare_df['Tål katt'] = medarbetare_df['Tål katt'].apply(lambda x: x == 'Ja')
    medarbetare_df['Man'] = medarbetare_df['Man'].apply(lambda x: x == 'Ja')
    medarbetare_df['Kvinna'] = medarbetare_df['Kvinna'].apply(lambda x: x == 'Ja')
    medarbetare_df['Körkort'] = medarbetare_df['Körkort'].apply(lambda x: x == 'Ja')
    medarbetare_df['Läkemedelsdelegering'] = medarbetare_df['Läkemedelsdelegering'].apply(lambda x: x == 'Ja')
    medarbetare_df['Insulindelegering'] = medarbetare_df['Insulindelegering'].apply(lambda x: x == 'Ja')
    medarbetare_df['Stomidelegering'] = medarbetare_df['Stomidelegering'].apply(lambda x: x == 'Ja')
    medarbetare_df['18 år el mer'] = medarbetare_df['18 år el mer'].apply(lambda x: x == 'Ja')

    # Create 'Capabilities' column based on boolean fields
    medarbetare_df['Capabilities'] = medarbetare_df.apply(lambda row: ','.join([
        'license' if row['Körkort'] else '',
        'dog_friendly' if row['Tål hund'] else '',
        'cat_friendly' if row['Tål katt'] else '',
        'man' if row['Man'] else '',
        'woman' if row['Kvinna'] else '',
        'medication' if row['Läkemedelsdelegering'] else '',
        'insulin' if row['Insulindelegering'] else '',
        'stoma' if row['Stomidelegering'] else '',
        '>18' if row['18 år el mer'] else ''
    ]).strip(','), axis=1)

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

def add_time_windows(brukare_df):
    """
    Add a 'time_windows' column to the brukare DataFrame based on the time period they need to be visited.
    Time periods include 'Morgon', 'Förmiddag', 'Lunch', 'Eftermiddag', 'Middag', 'Tidig kväll', 'Sen kväll'.
    Each time period is mapped to a specific time window (start and end time).
    """
    
    # Define the time windows for each time period (hours of the day)
    time_window_dict = {
        "Morgon": (8 * 60, 10 * 60),       # From 8:00 to 10:00 (in minutes)
        "Förmiddag": (10 * 60, 12 * 60),   # From 10:00 to 12:00 (in minutes)
        "Lunch": (12 * 60, 13 * 60),       # From 12:00 to 13:00
        "Eftermiddag": (13 * 60, 16 * 60), # From 13:00 to 16:00
        "Middag": (16 * 60, 18 * 60),      # From 16:00 to 18:00
        "Tidig kväll": (18 * 60, 20 * 60), # From 18:00 to 20:00
        "Sen kväll": (20 * 60, 22 * 60)    # From 20:00 to 22:00
    }

    # Add a 'time_windows' column based on the time period (if column 'Tid' exists in brukare_df)
    if 'Tid' in brukare_df.columns:
        brukare_df['time_windows'] = brukare_df['Tid'].apply(lambda period: time_window_dict.get(period, (0, 24 * 60)))  # Default: 00:00 to 24:00 if time period is not found
    else:
        # Handle case where 'Tid' column doesn't exist or is missing
        brukare_df['time_windows'] = [(0, 24 * 60)] * len(brukare_df)  # Default: whole day available

    return brukare_df
