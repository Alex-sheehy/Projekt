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
    brukare_df['Kräver körkort'] = brukare_df['Kräver körkort'].apply(lambda x: x == 'Ja')
    brukare_df['Röker'] = brukare_df['Röker'].apply(lambda x: x == 'Ja')
    brukare_df['Har hund'] = brukare_df['Har hund'].apply(lambda x: x == 'Ja')
    brukare_df['Har katt'] = brukare_df['Har katt'].apply(lambda x: x == 'Ja')
    brukare_df['Kräver >18'] = brukare_df['Kräver >18'].apply(lambda x: x == 'Ja')

    return brukare_df

def rensa_medarb_data(medarbetare_df):
    """
    Rensar medarbetar datan så att ja och nej blir istället "TRUE" eller "FALSE"
    """
    # Rename 'Unnamed: 0' to 'Medarbetare' for medarbetare_df
    medarbetare_df.rename(columns={'Unnamed: 0': 'Medarbetare'}, inplace=True)

    # Fill missing values in other columns with placeholder '-'
    medarbetare_df.fillna('-', inplace=True)
    
    columns_medarbetare = list(medarbetare_df)

    for column in columns_medarbetare[1:]:
        medarbetare_df[column] = medarbetare_df[column].apply(lambda x: x == 'Ja')

    return medarbetare_df

def skapa_brukare_dict(brukare_df,tider,regex_filters):
    """
    Skapar en dict med data om brukarna i det givna tidsfönstret
    """
    index = 0
    brukare_dict = {}
    for tid in tider:
        regex_filter = regex_filters[index]
        tidsfönster_brukare_dict = {}
        #Tar ut individers krav under detta tidsfönster
        läkemedel = brukare_df[brukare_df["Behöver läkemedel"].str.contains(regex_filter, na=False)]
        insulin = brukare_df[brukare_df["Behöver insulin"].str.contains(regex_filter, na=False)]
        stomi = brukare_df[brukare_df["Har stomi"].str.contains(regex_filter, na=False)]
        dubbelbemanning_df = brukare_df[brukare_df[tid].str.contains(r'\*', na=False)]
        
        #Tar ut de individer som ska ha besök i detta tidsfönster
        individer = brukare_df[brukare_df[tid].apply(
            lambda x: isinstance(x, int) or 
            (isinstance(x, str) and bool(re.fullmatch(r"\d+\*\d+", x))))]

        for index, row in individer.iterrows():
            individ = row["Individ"]

            if läkemedel["Individ"].str.contains(individ, regex = False).any() == True:
                behöver_läkemedel = True
            else:
                behöver_läkemedel = False
        
            if insulin["Individ"].str.contains(individ, regex = False).any() == True:
                behöver_insulin = True
            else:
                behöver_insulin = False

            if stomi["Individ"].str.contains(individ, regex = False).any() == True:
                har_stomi = True
            else:
                har_stomi = False
            
            if dubbelbemanning_df["Individ"].str.contains(individ, regex = False).any() == True:
                dubbelbemanning = True
                dubbel_tid = row[tid].split('*')
                riktig_tid = dubbel_tid[0]
                #Skapar en dict som har en dict i sig för alla individer i detta tidsfönster
                tidsfönster_brukare_dict[individ] = {
                    "Tid": riktig_tid,
                    "Dubbelbemanning": dubbelbemanning,
                    "Behöver läkemedel": behöver_läkemedel,
                    "Kräver körkort": row["Kräver körkort"],
                    "Behöver insulin": behöver_insulin,
                    "Har stomi": har_stomi,
                    "Har hund": row["Har hund"],
                    "Har katt": row["Har katt"],
                    "Kräver>18": row["Kräver >18"]
                }
            else:
                dubbelbemanning = False
                #Skapar en dict som har en dict i sig för alla individer i detta tidsfönster
                tidsfönster_brukare_dict[individ] = {
                    "Tid": row[tid],
                    "Dubbelbemanning": dubbelbemanning,
                    "Behöver läkemedel": behöver_läkemedel,
                    "Kräver körkort": row["Kräver körkort"],
                    "Behöver insulin": behöver_insulin,
                    "Har stomi": har_stomi,
                    "Har hund": row["Har hund"],
                    "Har katt": row["Har katt"],
                    "Kräver>18": row["Kräver >18"]
                }
        
        brukare_dict[tid] = tidsfönster_brukare_dict
        index =+ 1

    return brukare_dict

def skapa_medarbetare_dict(medarbetare_df, tider, reges_filters):
    """
    Skapar en dict med data om medarbetarna för den givna tidsfönstret 
    """
    medarbetare_dict = {}
    index = 0
    for tid in tider: 
        tidsfönster_medarbetare_dict = {}
        reges_filter = reges_filters[index]

        for index, row in medarbetare_df.iterrows():
            medarbetare = row["Medarbetare"]

            #Skapar en dict som har en dict i sig för alla medarbetare
            tidsfönster_medarbetare_dict[medarbetare] = {
                "Tål hund": row["Tål hund"],
                "Tål katt": row["Tål katt"],
                "Man": row["Man"],
                "Kvinna": row["Kvinna"],
                "Körkort": row["Körkort"],
                "Läkemedelsdelegering": row["Läkemedelsdelegering"],
                "Insulindelegering": row["Insulindelegering"],
                "Stomidelegering":row["Stomidelegering"],        
                "18 år el mer": row["18 år el mer"]
            }

        medarbetare_dict[tid] = tidsfönster_medarbetare_dict
        index =+ 1
    return medarbetare_dict


def skapa_dag_dict(brukare_dag_dict, medarbetare_dag_dict, regex_mönster):
    """
    Skapar en dict för hela dagen. Där även den lägger in speciella villkor
    som gäller för det specefika dagen. 
    """
    dag_dict = {}

    #Kollar dusch villkor


    #Kollar aktiverings villkor





    return dag_dict


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

    tid = ["Morgon", "Förmiddag", "Lunch", "Eftermiddag", "Middag", "Tidig kväll", "Sen kväll"]
    regex_tid_mönster = [ r'\b[mM]org\b', r'\b[fF]m\b', r'\b[lL]unch\b',  r'\b[eE]m\b', r'\b[mM]iddag\b', 
                         r'\b[tT]idig kväll\b', r'\b[sS]en kväll\b']
    #Skapar dicts för alla olika tidsfönster som besök kan ske med data om brukare
    brukare_dag_dict = skapa_brukare_dict(brukare_df, tid, regex_tid_mönster)

    #Test print, den ska bort!
    morgDict = brukare_dag_dict["Morgon"]
    print(morgDict)

    #Skapa dicts för medarebetare och dess villkor, för de olika tidsfönstrena
    #TODO: Fixa då att det faktiskt är någon skillnad på medarbetarna mellan de olika tidsfönstrena
    medarbetare_dag_dict = skapa_medarbetare_dict(medarbetare_df, tid, regex_tid_mönster)

    #Skapar dicts för alla veckodagar
    mån_dict = skapa_dag_dict(brukare_dag_dict, medarbetare_dag_dict, r'/b[mM]ån')
    
    
    #TODO fixa så att kartan kan användas på rätt sätt
    #loadNodeMap()
    
    #print(brukare_df)
    #print(brukare_df)
    #print(medarbetare_df)

if __name__ == '__main__':
    main()
