import pandas as pd
import numpy as np

# Läs in filen
file_path = "Studentuppgift fiktiv planering Hugo.xlsx"
data = pd.read_excel(file_path, sheet_name='Brukare Rensad')

# 1. Konvertera alla kolumner till strängar innan vi fyller nullvärden
data = data.astype(str)
data.replace("nan", "-", inplace=True)  # Ersätt alla "nan" strängar med "-"

# 2. Konvertera tid (Morgon, Lunch, etc.) till minuter och hantera multiplikator (ex: "30*2")
def convert_to_minutes(value):
    try:
        if isinstance(value, str) and "*" in value:
            base_time, multiplier = value.split('*')
            return int(float(base_time)), int(multiplier)  # Returnera både tid och multiplikator
        elif isinstance(value, str) and value.replace('.', '', 1).isdigit():  # Hantera flyttal
            return int(float(value)), 1  # Om ingen multiplikator finns, returnera 1 som standard
        else:
            return 0, 1  # Om inget tidvärde finns, returnera 0 min och 1 person
    except ValueError:
        return 0, 1  # Om det inte går att konvertera

# Använd funktionen för att konvertera tidsvärden
for time_column in ['Morgon', 'Lunch', 'Middag', 'Sen kväll', 'Förmiddag', 'Eftermiddag', 'Tidig kväll']:
    data[[time_column, f"{time_column}_personer"]] = data[time_column].apply(lambda x: pd.Series(convert_to_minutes(x)))

# 3. Funktion för att dela upp tid och dagar för Dusch och Aktivering
def parse_dusch_aktivering(tid, dagar):
    try:
        if tid != '-' and tid != 'nan':
            if '*' in tid:
                base_time, multiplier = tid.split('*')
                total_time = int(float(base_time)) * int(multiplier)
                personer = int(multiplier)
            else:
                total_time = int(float(tid))  # Hantera flyttal som '60.0'
                personer = 1  # Om ingen multiplikator finns, är det 1 person
        else:
            total_time = None  # Om ingen tid är angiven
            personer = 0  # Om ingen tid finns, behövs ingen person

        if dagar != '-' and dagar != 'nan':
            day_list = [day.strip() for day in dagar.split(',')]
        else:
            day_list = []  # Tom lista om inga dagar är angivna

        return {'tid': total_time, 'dagar': day_list, 'personer': personer}
    except ValueError:
        return {'tid': None, 'dagar': [], 'personer': 0}

# Använd funktionen för Dusch och Aktivering
data['Dusch_Schema'] = data.apply(lambda row: parse_dusch_aktivering(row['Dusch'], row['Dag.7']), axis=1)
data['Aktivering_Schema'] = data.apply(lambda row: parse_dusch_aktivering(row['Aktivering'], row['Dag.8']), axis=1)

# 4. Konvertera binära värden (t.ex. Ja/Nej) till boolska värden
binary_columns = ['Kräver körkort', 'Röker', 'Har hund', 'Har katt', 'Kräver man', 'Kräver kvinna', 'Kräver >18']
data[binary_columns] = data[binary_columns].replace({'Ja': True, 'Nej': False, '-': False})


class Individ:
    def __init__(self, id, kor_kort, roker, har_hund, har_katt, krav_man, krav_kvinna, krav_18,
                 morgon_tid, morgon_personer, formiddag_tid, formiddag_personer, lunch_tid, lunch_personer,
                 eftermiddag_tid, eftermiddag_personer, middag_tid, middag_personer,
                 tidig_kvall_tid, tidig_kvall_personer, sen_kvall_tid, sen_kvall_personer,
                 dusch_schema, aktivering_schema, lakemedel, insulin, stomi):
        self.id = id
        self.kor_kort = kor_kort
        self.roker = roker
        self.har_hund = har_hund
        self.har_katt = har_katt
        self.krav_man = krav_man
        self.krav_kvinna = krav_kvinna
        self.krav_18 = krav_18
        self.morgon_tid = morgon_tid
        self.morgon_personer = morgon_personer
        self.formiddag_tid = formiddag_tid
        self.formiddag_personer = formiddag_personer
        self.lunch_tid = lunch_tid
        self.lunch_personer = lunch_personer
        self.eftermiddag_tid = eftermiddag_tid
        self.eftermiddag_personer = eftermiddag_personer
        self.middag_tid = middag_tid
        self.middag_personer = middag_personer
        self.tidig_kvall_tid = tidig_kvall_tid
        self.tidig_kvall_personer = tidig_kvall_personer
        self.sen_kvall_tid = sen_kvall_tid
        self.sen_kvall_personer = sen_kvall_personer
        self.dusch_schema = dusch_schema
        self.aktivering_schema = aktivering_schema
        self.lakemedel = lakemedel
        self.insulin = insulin
        self.stomi = stomi

    def __repr__(self):
        return (f"Individ({self.id}, Morgon: {self.morgon_tid} min, Förmiddag: {self.formiddag_tid} min, "
                f"Lunch: {self.lunch_tid} min, Eftermiddag: {self.eftermiddag_tid} min, Middag: {self.middag_tid} min, "
                f"Tidig kväll: {self.tidig_kvall_tid} min, Sen kväll: {self.sen_kvall_tid} min, "
                f"Läkemedel: {self.lakemedel}, Insulin: {self.insulin}, Stomi: {self.stomi}, "
                f"Dusch: {self.dusch_schema}, Aktivering: {self.aktivering_schema})")


# Skapa instanser av klassen Individ för varje rad i data
individer = []
for index, row in data.iterrows():
    individ = Individ(
        id=row['Individ'],
        kor_kort=row['Kräver körkort'],
        roker=row['Röker'],
        har_hund=row['Har hund'],
        har_katt=row['Har katt'],
        krav_man=row['Kräver man'],
        krav_kvinna=row['Kräver kvinna'],
        krav_18=row['Kräver >18'],
        morgon_tid=row['Morgon'],
        morgon_personer=row['Morgon_personer'],
        formiddag_tid=row['Förmiddag'],
        formiddag_personer=row['Förmiddag_personer'],
        lunch_tid=row['Lunch'],
        lunch_personer=row['Lunch_personer'],
        eftermiddag_tid=row['Eftermiddag'],
        eftermiddag_personer=row['Eftermiddag_personer'],
        middag_tid=row['Middag'],
        middag_personer=row['Middag_personer'],
        tidig_kvall_tid=row['Tidig kväll'],
        tidig_kvall_personer=row['Tidig kväll_personer'],
        sen_kvall_tid=row['Sen kväll'],
        sen_kvall_personer=row['Sen kväll_personer'],
        dusch_schema=row['Dusch_Schema'],
        aktivering_schema=row['Aktivering_Schema'],
        lakemedel={  # Läkemedel vid olika tider
            'morgon': row['Läkemedel'],
            'formiddag': row['Läkemedel.1'],
            'lunch': row['Läkemedel.2'],
            'eftermiddag': row['Läkemedel.3'],
            'middag': row['Läkemedel.4'],
            'tidig_kvall': row['Läkemedel.5'],
            'sen_kvall': row['Läkemedel.6']
        },
        insulin={  # Insulin vid olika tider
            'morgon': row['Insulin'],
            'formiddag': row['Insulin.1'],
            'lunch': row['Insulin.2'],
            'eftermiddag': row['Insulin.3'],
            'middag': row['Insulin.4'],
            'tidig_kvall': row['Insulin.5'],
            'sen_kvall': row['Insulin.6']
        },
        stomi={  # Stomi vid olika tider
            'morgon': row['Stomi'],
            'formiddag': row['Stomi.1'],
            'lunch': row['Stomi.2'],
            'eftermiddag': row['Stomi.3'],
            'middag': row['Stomi.4'],
            'tidig_kvall': row['Stomi.5'],
            'sen_kvall': row['Stomi.6']
        }
    )
    individer.append(individ)

# Hitta scheman för varje individ
for individ in individer:
    print(f"{individ.id}:")
    print(f"- Morgon: {individ.morgon_tid} min, {individ.morgon_personer} person(er), Läkemedel: {individ.lakemedel['morgon']}, Insulin: {individ.insulin['morgon']}, Stomi: {individ.stomi['morgon']}")
    print(f"- Förmiddag: {individ.formiddag_tid} min, {individ.formiddag_personer} person(er), Läkemedel: {individ.lakemedel['formiddag']}, Insulin: {individ.insulin['formiddag']}, Stomi: {individ.stomi['formiddag']}")
    print(f"- Lunch: {individ.lunch_tid} min, {individ.lunch_personer} person(er), Läkemedel: {individ.lakemedel['lunch']}, Insulin: {individ.insulin['lunch']}, Stomi: {individ.stomi['lunch']}")
    print(f"- Eftermiddag: {individ.eftermiddag_tid} min, {individ.eftermiddag_personer} person(er), Läkemedel: {individ.lakemedel['eftermiddag']}, Insulin: {individ.insulin['eftermiddag']}, Stomi: {individ.stomi['eftermiddag']}")
    print(f"- Middag: {individ.middag_tid} min, {individ.middag_personer} person(er), Läkemedel: {individ.lakemedel['middag']}, Insulin: {individ.insulin['middag']}, Stomi: {individ.stomi['middag']}")
    print(f"- Tidig kväll: {individ.tidig_kvall_tid} min, {individ.tidig_kvall_personer} person(er), Läkemedel: {individ.lakemedel['tidig_kvall']}, Insulin: {individ.insulin['tidig_kvall']}, Stomi: {individ.stomi['tidig_kvall']}")
    print(f"- Sen kväll: {individ.sen_kvall_tid} min, {individ.sen_kvall_personer} person(er), Läkemedel: {individ.lakemedel['sen_kvall']}, Insulin: {individ.insulin['sen_kvall']}, Stomi: {individ.stomi['sen_kvall']}")

    # Hantera Duschschema
    if individ.dusch_schema['tid'] is not None:
        dusch_info = f"Dusch {individ.dusch_schema['tid']} min med {individ.dusch_schema['personer']} person(er) på {', '.join(individ.dusch_schema['dagar'])}"
    else:
        dusch_info = f"Dusch på {', '.join(individ.dusch_schema['dagar'])}" if individ.dusch_schema['dagar'] else "Ingen dusch schemalagd"
    
    # Hantera Aktiveringsschema
    if individ.aktivering_schema['tid'] is not None:
        aktivering_info = f"Aktivering {individ.aktivering_schema['tid']} min med {individ.aktivering_schema['personer']} person(er) på {', '.join(individ.aktivering_schema['dagar'])}"
    else:
        aktivering_info = f"Aktivering på {', '.join(individ.aktivering_schema['dagar'])}" if individ.aktivering_schema['dagar'] else "Ingen aktivering schemalagd"

    print(f"- {dusch_info}")
    print(f"- {aktivering_info}")
    print()


data_medarbetare = pd.read_excel(file_path, sheet_name='Medarbetare', header=2)

# Konvertera alla kolumner till strängar innan vi fyller nullvärden
data_medarbetare = data_medarbetare.astype(str)
data_medarbetare.replace("nan", "-", inplace=True)  # Ersätt alla "nan" strängar med "-"

# Konvertera binära värden (t.ex. Ja/Nej) till boolska värden
binary_columns = ['Tål hund', 'Tål katt', 'Tål rök', 'Man', 'Kvinna', 'Körkort', 
                  'Läkemedelsdelegering', 'Insulindelegering', 'Stomidelegering', '18 år el mer']
data_medarbetare[binary_columns] = data_medarbetare[binary_columns].replace({'Ja': True, 'Nej': False, '-': False})

# Klassdefinition för Medarbetare
class Medarbetare:
    def __init__(self, id, tal_hund, tal_katt, tal_rok, man, kvinna, kor_kort, lakemedel_delegering, insulin_delegering, stomi_delegering, ar_18_el_mer):
        self.id = id
        self.tal_hund = tal_hund
        self.tal_katt = tal_katt
        self.tal_rok = tal_rok
        self.man = man
        self.kvinna = kvinna
        self.kor_kort = kor_kort
        self.lakemedel_delegering = lakemedel_delegering
        self.insulin_delegering = insulin_delegering
        self.stomi_delegering = stomi_delegering
        self.ar_18_el_mer = ar_18_el_mer

    def __repr__(self):
        return (f"Medarbetare({self.id}, Tål hund: {self.tal_hund}, Tål katt: {self.tal_katt}, Tål rök: {self.tal_rok}, "
                f"Man: {self.man}, Kvinna: {self.kvinna}, Körkort: {self.kor_kort}, "
                f"Läkemedelsdelegering: {self.lakemedel_delegering}, Insulindelegering: {self.insulin_delegering}, "
                f"Stomidelegering: {self.stomi_delegering}, 18 år eller mer: {self.ar_18_el_mer})")

# Skapa instanser av klassen Medarbetare för varje rad i data
medarbetare_list = []
for index, row in data_medarbetare.iterrows():
    medarbetare = Medarbetare(
        id=row['Medarbetare'],
        tal_hund=row['Tål hund'],
        tal_katt=row['Tål katt'],
        tal_rok=row['Tål rök'],
        man=row['Man'],
        kvinna=row['Kvinna'],
        kor_kort=row['Körkort'],
        lakemedel_delegering=row['Läkemedelsdelegering'],
        insulin_delegering=row['Insulindelegering'],
        stomi_delegering=row['Stomidelegering'],
        ar_18_el_mer=row['18 år el mer']
    )
    medarbetare_list.append(medarbetare)

# Visa alla medarbetare
for medarbetare in medarbetare_list:
    print(medarbetare)


# Funktion för att kontrollera om en medarbetare kan besöka en individ
def kan_besoka(medarbetare, individ):
    if medarbetare.kor_kort != individ.kor_kort:
        return False
    if medarbetare.tal_hund == False and individ.har_hund == True:
        return False
    if medarbetare.tal_katt == False and individ.har_katt == True:
        return False
    if medarbetare.man == False and individ.krav_man == True:
        return False
    if medarbetare.kvinna == False and individ.krav_kvinna == True:
        return False
    if medarbetare.lakemedel_delegering == False and any([v == 'Ja' for v in individ.lakemedel.values()]):
        return False
    if medarbetare.insulin_delegering == False and any([v == 'Ja' for v in individ.insulin.values()]):
        return False
    if medarbetare.stomi_delegering == False and any([v == 'Ja' for v in individ.stomi.values()]):
        return False
    if medarbetare.ar_18_el_mer == False and individ.krav_18 == True:
        return False
    return True
'''
# Testa funktionen
for medarbetare in medarbetare_list:
    for individ in individer:
        if kan_besoka(medarbetare, individ):
            print(f"{medarbetare.id} kan besöka {individ.id}")
        else:
            print(f"{medarbetare.id} kan INTE besöka {individ.id}")
'''




    