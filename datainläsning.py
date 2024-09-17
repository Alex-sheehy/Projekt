import pandas as pd
import numpy as np
import scipy.optimize as opt
import osmnx as ox
import re
import matplotlib.pylab as plt


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
    Rensar data på brukarna till endast rader där individ namn finns och ändrar så att
    det är "TRUE" eller "FALSE" på ja och nej datan
    """
    # Rename 'Unnamed: 0' to 'Individ' for brukare_df
    brukare_df.rename(columns={'Unnamed: 0': 'Individ'}, inplace=True)
   
    # Remove brukare with missing or invalid 'Individ' or 'Adress'
    brukare_df = brukare_df.dropna(subset=['Individ']).copy()
    
    # Fill missing values in other columns with placeholder '-'
    brukare_df.fillna('-', inplace=True)
    

    # Convert relevant columns to boolean
    #brukare_df['Kräver körkort'] = brukare_df['Kräver körkort'].apply(lambda x: x == 'Ja')
    #medarbetare_df['Körkort'] = medarbetare_df['Körkort'].apply(lambda x: x == 'Ja')

    brukare_df['Kräver körkort'] = brukare_df['Kräver körkort'].apply(lambda x: x == 'Ja')

    #brukare_df['Behöver insulin'] = brukare_df['Behöver insulin'].apply(lambda x: x == True)
    
    brukare_df['Röker'] = brukare_df['Röker'].apply(lambda x: x == 'Ja')
    brukare_df['Har hund'] = brukare_df['Har hund'].apply(lambda x: x == 'Ja')
    brukare_df['Har katt'] = brukare_df['Har katt'].apply(lambda x: x == 'Ja')
    brukare_df['Kräver >18'] = brukare_df['Kräver >18'].apply(lambda x: x == 'Ja')

    return brukare_df

def rensa_medarb_data(medarbetare_df):
    """
    Rensar medarbetar datan så att ja och nej blir istället "TRUE" eller "FALSE"
    """
    #FIXME Är osäker på om denna function fungerar som önskat
    
    # Rename 'Unnamed: 0' to 'Medarbetare' for medarbetare_df
    medarbetare_df.rename(columns={'Unnamed: 0': 'Medarbetare'}, inplace=True)

    # Fill missing values in other columns with placeholder '-'
    medarbetare_df.fillna('-', inplace=True)
    
    columns_medarbetare = list(medarbetare_df)

    for column in columns_medarbetare[1:]:
        medarbetare_df[column] = medarbetare_df[column].apply(lambda x: x == 'Ja')


    return medarbetare_df

def skapa_brukare_dict(brukare_df,tid,regex_filter):
    """
    Skapar en dict med data om brukarna i det givna tidsfönstret
    """
    brukare_dict = {}

    #Tar ut individers morgon krav
    läkemedel = brukare_df[brukare_df["Behöver läkemedel"].str.contains(regex_filter, na=False)]
    
    insulin = brukare_df[brukare_df["Behöver insulin"].str.contains(regex_filter, na=False)]
    stomi = brukare_df[brukare_df["Har stomi"].str.contains(regex_filter, na=False)]

    #Tar ut de individer som ska ha besök på mrogonen
    individer = brukare_df[brukare_df[tid].apply(lambda x: isinstance(x, int))]

    for index, row in individer.iterrows():
        individ = row["Individ"]

        if individ in läkemedel["Individ"]:
            behöver_läkemedel = True
        else:
            behöver_läkemedel = False
        
        if individ in insulin["Individ"]:
            behöver_insulin = True
        else:
            behöver_insulin = False

        if individ in stomi["Individ"]:
            har_stomi = True
        else:
            har_stomi = False

        #Skapar en dict som har en dict i sig för alla individer som ska ha besök på morgonen
        brukare_dict[individ] = {
            "Tid": row[tid],
            "Behöver läkemedel": behöver_läkemedel,
            "Kräver körkort": row["Kräver körkort"],
            "Behöver insulin": behöver_insulin,
            "Har stomi": har_stomi,
            "Har hund": row["Har hund"],
            "Har katt": row["Har katt"],
            "Kräver>18": row["Kräver >18"]
        }

    return brukare_dict

def skapa_medarbetare_dict(medarbetare_df, tid, reges_pattern):
    """
    Skapar en dict med data om medarbetarna för den givna tidsfönstret 
    """
    medarbetare_dict = {}


    return medarbetare_dict

def load_node_map():
    # Define the place name for Skellefteå Kommun
    place_name = "Skellefteå, Västerbotten, Sweden"

    # Download the road network for driving
    G = ox.graph_from_place(place_name, network_type='drive')

    # Plot the road network of Skellefteå
    fig, ax = ox.plot_graph(G, node_size=1, edge_color='white', edge_linewidth=0.1)
    plt.show()


def main():

    data = ladda_data("Studentuppgift fiktiv planering.xlsx")
    
    #Data rensning
    brukare_df = rensa_brukar_data(data["brukare"])
    medarbetare_df = rensa_medarb_data( data["medarbetare"])
    
    #TODO fixa så att "*2" i tid blir hanterat korrekt

    #Skapar dicts för alla olika tidsfönster som besök kan ske med data om brukare
    brukare_morg_dict = skapa_brukare_dict(brukare_df, "Morgon", r'\b[mM]org\b')
    brukare_fm_dict = skapa_brukare_dict(brukare_df, "Förmiddag", r'\b[fF]m\b')
    brukare_lunch_dict = skapa_brukare_dict(brukare_df, "Lunch", r'\b[lL]unch\b')
    burkare_em_dict = skapa_brukare_dict(brukare_df, "Eftermiddag", r'\b[eE]m\b')
    brukare_middag_dict = skapa_brukare_dict(brukare_df, "Middag", r'\b[mM]iddag\b')
    burkare_tidig_kväll_dict = skapa_brukare_dict(brukare_df, "Tidig kväll", r'\b[tT]idig kväll\b')
    brukare_sen_kväll_dict = skapa_brukare_dict(brukare_df, "Sen kväll", r'\b[sS]en kväll\b')

    #print(brukar_morg_dict)
    for key in brukare_lunch_dict.keys():
        print(brukare_lunch_dict[key])

    #Skapa dicts för medarebetare och dess villkor, för de olika tidsfönstrena
    medarbetare_morg_dict = skapa_medarbetare_dict(medarbetare_df, "Morgon", r'\b[mM]org\b')
    medarbetare_fm_dict = skapa_medarbetare_dict(medarbetare_df, "Förmiddag", r'\b[fF]m\b')
    medarbetare_lunch_dict = skapa_medarbetare_dict(medarbetare_df, "Lunch", r'\b[lL]unch\b')
    medarbetare_em_dict = skapa_medarbetare_dict(medarbetare_df, "Eftermiddag", r'\b[eE]m\b')
    medarbetare_middag_dict = skapa_medarbetare_dict(medarbetare_df, "Middag", r'\b[mM]iddag\b')
    medarbetare_tidig_kväll_dict = skapa_medarbetare_dict(medarbetare_df, "Tidig kväll", r'\b[tT]idig kväll\b')
    medarbetare_sen_kväll_dict = skapa_medarbetare_dict(medarbetare_df, "Sen kväll", r'\b[sS]en kväll\b')

    #TODO fixa så att kartan kan användas på rätt sätt
    #loadNodeMap()
    
    #print(brukare_df)
    #print(brukare_df)
    #print(medarbetare_df)

if __name__ == '__main__':
    main()
