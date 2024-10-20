from data_processing import ladda_data, rensa_medarb_data
import pandas as pd
import re

def skapa_brukare_df(brukare_df,tidsfönsterna,regex_filters):
    """
    Input: brukare_df, Det ska vara datan direkt från "ladda_data" funktionen i data_processing
    tidsfönstrena, alla olika tidsfönster som tuple av sträng och tidsinterval
    regex_filters, regex för de olika tidsfönstrena

    Skapar en dataframe med data om brukarna i det givna tidsfönstret
    """
    brukare_df.rename(columns={'Unnamed: 0': 'Individ'}, inplace=True)

    index = 0
    tidsfönster_brukare_data = []
    for tidsfönster in tidsfönsterna:
        regex_filter = regex_filters[index]
        #Tar ut individers krav under detta tidsfönster
        läkemedel = brukare_df[brukare_df["Behöver läkemedel"].str.contains(regex_filter, na=False)]
        insulin = brukare_df[brukare_df["Behöver insulin"].str.contains(regex_filter, na=False)]
        stomi = brukare_df[brukare_df["Har stomi"].str.contains(regex_filter, na=False)]
        dubbelbemanning_df = brukare_df[brukare_df[tidsfönster[0]].str.contains(r'\*', na=False)]
        
        #Tar ut de individer som ska ha besök i detta tidsfönster
        individer = brukare_df[brukare_df[tidsfönster[0]].apply(
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
                dubbel_tid = row[tidsfönster[0]].split('*')
                #Tar ut den tiden för besöket, hanterar olika format som 2*30 och 30*2
                if int(dubbel_tid[0]) > int(dubbel_tid[1]):
                    riktig_tid = int(dubbel_tid[0])
                else:
                    riktig_tid = int(dubbel_tid[1])
                #Skapar en rad i dataframe för besöket som ska utföras. 
                # Det blir dubbla rader nu eftersom det ska vara dubbelbemanning                
                
                dubbel = 2 #För att det är dubbelbemmaning
                for i in range(dubbel):
                    tidsfönster_brukare_data.append({
                        "Individ": individ,
                        "Tid": riktig_tid,
                        "Tidsfönster": tidsfönster,
                        "Constraints": ",".join(filter(None,
                            ['license' if row.get('Kräver körkort', False) == "Ja" else '',
                            'smoker' if row.get('Röker', False) == "Ja" else  '',
                            'dog' if row.get('Har hund', False) == "Ja" else '',
                            'cat' if row.get('Har katt', False) == "Ja" else '',
                            '>18' if row.get('Kräver >18', False) == "Ja"else '',
                            'medication' if behöver_läkemedel else '',
                            'insulin' if behöver_insulin else '',
                            'stoma' if har_stomi else '']
                        )).strip(',')
                    })
                 
            else:
                #Skapar en rad i dataframen för besöket som ska utföras
                
                tidsfönster_brukare_data.append({
                        "Individ": individ,
                        "Tid": row[tidsfönster[0]],
                        "Tidsfönster": tidsfönster,
                        "Constraints": ",".join(filter(None,
                            ['license' if row.get('Kräver körkort', False) == "Ja" else '',
                            'smoker' if row.get('Röker', False) == "Ja" else '',
                            'dog' if row.get('Har hund', False) == "Ja" else '',
                            'cat' if row.get('Har katt', False) == "Ja" else '',
                            '>18' if row.get('Kräver >18', False) == "Ja" else '',
                            'medication' if behöver_läkemedel else '',
                            'insulin' if behöver_insulin else '',
                            'stoma' if har_stomi else '']
                        )).strip(',')
                    })
        
        index =+ 1

    return pd.DataFrame(tidsfönster_brukare_data)


def skapa_brukare_dag_df(brukare_df, brukare_tidsfönster_df, regex):
    """
    Input: brukar_df, brukare delen av data gfrån ladda_data
    brukare_tidsfönster_df, dataframe från skapa_brukare_df funktionen
    regex, filter för den dagaen som man vill ha data för.

    Skapar en dataframe för den dagens regex filter som man kaller på den med
    """

    tid_regex = r'\b\d{2}\b'
    #Uppdaterar för dusch villkor
    dusch_behov_df = brukare_df[brukare_df["Dusch"].str.contains(regex, na=False)]
    #Itererar över de individer som ska ha dusch besök och sätter in det på förmiddagen
    for index, row in dusch_behov_df.iterrows():
        
        dusch_tid = re.search(tid_regex,row["Dusch"])
        if dusch_tid == None:
            #Om det inte finns en bestämd duschtid så sätts det till 30 min
            dusch_tid = 30
        else:
            dusch_tid = int(dusch_tid.group())
        
        krav_på_man = "vid dusch" in str(row["Kräver man"])
        krav_på_kvinna = "vid dusch" in str(row["Kräver kvinna"])


        #Kollar om ett besök redan ska ske på förmiddagen, om inte så lägger vi in ett nytt
        if row["Individ"] in brukare_tidsfönster_df[brukare_tidsfönster_df["Tidsfönster"].apply(lambda x: x[0] == "Förmiddag")]["Individ"].values:
            #Uppdaterar tiden för besöket
            orginal_besökstid = brukare_tidsfönster_df.loc[
                (brukare_tidsfönster_df["Tidsfönster"].apply(lambda x: x[0] == "Förmiddag")) & 
                (brukare_tidsfönster_df["Individ"] == row["Individ"]), "Tid"].values
            
            ny_besökstid = [int(tid) + dusch_tid for tid in orginal_besökstid]

            orginal_constraints = brukare_tidsfönster_df.loc[(
                brukare_tidsfönster_df["Tidsfönster"].apply(lambda x: x[0] =="Förmiddag")) & (
                brukare_tidsfönster_df["Individ"] == row["Individ"]), "Constraints"].values
            
            new_constraints = ",".join(filter(None,[str(orginal_constraints).strip("[]\'"), 
                                    'man' if krav_på_man else '',
                                    'woman' if krav_på_kvinna else '']
                                    )).strip(',')

            brukare_tidsfönster_df.loc[(
                brukare_tidsfönster_df["Tidsfönster"].apply(lambda x: x[0] =="Förmiddag")) & (
                brukare_tidsfönster_df["Individ"] == row["Individ"]), "Tid"] = ny_besökstid
            
            brukare_tidsfönster_df.loc[(
                brukare_tidsfönster_df["Tidsfönster"].apply(lambda x: x[0] =="Förmiddag")) & (
                brukare_tidsfönster_df["Individ"] == row["Individ"]), "Constraints"] = new_constraints
        else:
            nytt_besök = pd.DataFrame([{
                "Individ": row["Individ"],
                "Tid": dusch_tid,
                "Tidsfönster": ("Förmiddag","9-11"),
                "Constraints": ",".join(filter(None,
                            ['license' if row.get('Kräver körkort', False) == "Ja" else '',
                            'smoker' if row.get('Röker', False) == "Ja" else '',
                            'dog' if row.get('Har hund', False) == "Ja" else '',
                            'cat' if row.get('Har katt', False) == "Ja" else '',
                            '>18' if row.get('Kräver >18', False) == "Ja" else '',
                            'man' if krav_på_man else '',
                            'woman' if krav_på_kvinna else '']
                            )).strip(',')}])
            
            brukare_tidsfönster_df = pd.concat([brukare_tidsfönster_df, nytt_besök], ignore_index=True)

    #Uppdaterar för aktiverings villkor
    aktiverings_behov_df = brukare_df[brukare_df["Aktivering"].str.contains(regex, na=False)]
    for index, row in aktiverings_behov_df.iterrows():
        aktiverings_tid = re.search(tid_regex,row["Aktivering"])
        if aktiverings_tid == None:
            #Om det inte finns en bestämd aktiveringstid så sätts det till 30 min
            aktiverings_tid = 30
        else:
            aktiverings_tid = int(aktiverings_tid.group())
              #Kollar om ett besök redan ska ske på förmiddagen, om inte så lägger vi in ett nytt
        
        if row["Individ"] in brukare_tidsfönster_df[brukare_tidsfönster_df["Tidsfönster"].apply(lambda x: x[0] == "Eftermiddag")]["Individ"].values:
            #Uppdaterar tiden för besöket
            orginal_besökstid = brukare_tidsfönster_df.loc[(
                brukare_tidsfönster_df["Tidsfönster"].apply(lambda x: x[0]=="Eftermiddag")) & (
                brukare_tidsfönster_df["Individ"] == row["Individ"]), "Tid"].values
            
            ny_besökstid = orginal_besökstid + aktiverings_tid

            brukare_tidsfönster_df.loc[(
                brukare_tidsfönster_df["Tidsfönster"].apply(lambda x: x[0]=="Eftermiddag")) & (
                brukare_tidsfönster_df["Individ"] == row["Individ"]), "Tid"] = ny_besökstid

        else:

            nytt_besök = pd.DataFrame([{
                "Individ": row["Individ"],
                "Tid": aktiverings_tid,
                "Tidsfönster": ("Eftermiddag","13-15"),
                "Constraints": ",".join(filter(None,
                            ['license' if row.get('Kräver körkort', False) == "Ja" else '',
                            'smoker' if row.get('Röker', False) == "Ja" else '',
                            'dog' if row.get('Har hund', False) == "Ja" else '',
                            'cat' if row.get('Har katt', False) == "Ja" else '',
                            '>18' if row.get('Kräver >18', False) == "Ja" else '']
                            )).strip(',')}])
            
            brukare_tidsfönster_df = pd.concat([brukare_tidsfönster_df, nytt_besök], ignore_index=True)  

    return brukare_tidsfönster_df

def addera_adress_till_df(fil,brukare_tidsfönster_df):   
    adress_till_koordinater = {}
    individ_till_adress = {}
    individ_num = 1

    with open(fil, 'r') as f:
        for line in f:
            #Delar upp adresserna i aderss och koordinater
            parts = line.strip().split(", ")
            adress = parts[0]
            adress = adress.split(".")[1].strip(" ")
            latitude =  float, parts[1].strip("()").split(", ")
            longitude = float, parts[2].strip("()").split(", ")
            individ = "Individ "+ str(individ_num)
            #Skapar en dict för adrss kopplat till koordinater
            adress_till_koordinater[adress] = {"Latitude": latitude, "Longitude": longitude}
            individ_till_adress[individ] = adress
            individ_num += 1

    brukare_tidsfönster_df["Individ"] = brukare_tidsfönster_df["Individ"].str.strip()

    #Nu adderar vi adress och koordinater till dataframe för dagen
    brukare_tidsfönster_df["Adress"] = brukare_tidsfönster_df["Individ"].map(individ_till_adress)
    brukare_tidsfönster_df["Latitude"] = brukare_tidsfönster_df["Adress"].map(lambda x: adress_till_koordinater[x]["Latitude"])
    brukare_tidsfönster_df["Longitude"] = brukare_tidsfönster_df["Adress"].map(lambda x: adress_till_koordinater[x]["Longitude"])

    brukare_tidsfönster_df["Latitude"] = brukare_tidsfönster_df["Latitude"].apply(lambda x: x[1] if isinstance(x, tuple) else x)
    brukare_tidsfönster_df["Longitude"] = brukare_tidsfönster_df["Longitude"].apply(lambda x: x[1] if isinstance(x, tuple) else x)

    brukare_tidsfönster_df["Latitude"] = brukare_tidsfönster_df["Latitude"].apply(lambda x: x[0] if isinstance(x, list) else x)
    brukare_tidsfönster_df["Longitude"] = brukare_tidsfönster_df["Longitude"].apply(lambda x: x[0] if isinstance(x, list) else x)


    return brukare_tidsfönster_df

def dataframe_creation(dag):

    dag = str(dag)

    # Test användning
    data = ladda_data("project/data/Studentuppgift fiktiv planering.xlsx")
    
    

    tidsfönster = [("Morgon","7-9"), ("Förmiddag","9-11"), ("Lunch","11-13"), ("Eftermiddag","13-15"), ("Middag","15-17"), ("Tidig kväll","17-19"), ("Sen kväll","19-21")]
    regex_tid_mönster = [ r'\b[mM]org\b', r'\b[fF]m\b', r'\b[lL]unch\b',  r'\b[eE]m\b', r'\b[mM]iddag\b', 
                         r'\b[tT]idig kväll\b', r'\b[sS]en kväll\b']

    #Skapar dicts för alla olika tidsfönster som besök kan ske med data om brukare
    brukare_tidsfönster_df = skapa_brukare_df(data["brukare"], tidsfönster, regex_tid_mönster)

    #De olika Regex för de olika dagarana
    #TODO: detta kan göras mer andvändarvänligt med if statement eller mapping 
    regex_dag_mönster = {"Måndag" : r'\b[mM]ån', "Tisdag" : r'\b[tT]is', "Onsdag" : r'\b[oO]ns', "Torsdag" : r'\b[tT]or', "Fredag" : r'\b[fF]re'}
    
    #Test med en mån dataframe
    dag_df = skapa_brukare_dag_df(data["brukare"], brukare_tidsfönster_df, regex_dag_mönster[dag.title()])
    
    dag_df = addera_adress_till_df("Project/data/UppdateradeAddresser.txt", dag_df)

    return dag_df
