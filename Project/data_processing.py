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

    # List of columns that should be converted to boolean values if they exist
    boolean_columns = [
        'Kräver körkort', 'Röker', 'Har hund', 'Har katt', 
        'Kräver >18', 'Kräver man', 'Kräver kvinna', 
        'Behöver läkemedel', 'Behöver insulin', 'Har stomi', 
        'Dubbelbemanning', 'Dusch', 'Aktivering'
    ]

    # Convert relevant columns to boolean, only if the column exists
    for column in boolean_columns:
        if column in brukare_df.columns:
            brukare_df[column] = brukare_df[column].apply(lambda x: 'Ja' in str(x))

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
    Reads addresses and coordinates from a file.
    """
    addresses = []
    with open(file_path, 'r') as file:
        for line in file:
            try:
                parts = line.split(", ", 1)
                address_part = parts[0].split('. ', 1)[1]
                coordinates = eval(parts[1].strip())
                if isinstance(coordinates, tuple) and len(coordinates) == 2:
                    addresses.append((address_part, coordinates))
            except (SyntaxError, IndexError, NameError, TypeError):
                continue
    return addresses

def assign_addresses_to_brukare(brukare_df, addresses):
    """
    Assigns addresses and coordinates to brukare.
    """
    if len(addresses) < len(brukare_df):
        raise ValueError("Not enough addresses for all brukare.")
    
    for i, (address, coordinates) in enumerate(addresses):
        if i < len(brukare_df):
            brukare_df.at[i, 'Address'] = address
            brukare_df.at[i, 'Latitude'] = coordinates[0]
            brukare_df.at[i, 'Longitude'] = coordinates[1]
    
    return brukare_df
