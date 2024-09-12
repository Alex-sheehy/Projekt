# This will handle loading and cleaning the Excel data for brukare and medarbetare.

import pandas as pd

def load_data(file_path):
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


def clean_data(brukare_df, medarbetare_df):
    """
    Clean and structure brukare and medarbetare data for analysis.
    """
    # Rename 'Unnamed: 0' to 'Individ' for brukare_df
    brukare_df.rename(columns={'Unnamed: 0': 'Individ'}, inplace=True)

    # Rename 'Unnamed: 0' to 'Medarbetare' for medarbetare_df
    medarbetare_df.rename(columns={'Unnamed: 0': 'Medarbetare'}, inplace=True)

    # Remove brukare with missing or invalid 'Individ' or 'Adress'
    brukare_df = brukare_df.dropna(subset=['Individ', 'Adress']).copy()
    brukare_df = brukare_df[brukare_df['Individ'] != '-']  # Remove rows where 'Individ' is '-'
    brukare_df = brukare_df[brukare_df['Adress'] != '-']  # Remove rows where 'Adress' is '-'
    
    # Fill missing values in other columns with placeholder '-'
    brukare_df.fillna('-', inplace=True)
    medarbetare_df.fillna('-', inplace=True)

    # Convert relevant columns to boolean
    brukare_df['Kräver körkort'] = brukare_df['Kräver körkort'].apply(lambda x: x == 'Ja')
    medarbetare_df['Körkort'] = medarbetare_df['Körkort'].apply(lambda x: x == 'Ja')

    return brukare_df, medarbetare_df

