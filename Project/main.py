from data_processing import ladda_data, rensa_brukar_data, rensa_medarb_data, read_addresses, assign_addresses_to_brukare
from route_creation import skapa_brukare_dict, skapa_medarbetare_dict, create_weekly_dict
from utils import check_visits

def main():
    # Load data from Excel file
    data = ladda_data("Project/data/Studentuppgift fiktiv planering.xlsx")
    
    # Clean brukare and medarbetare data
    brukare_df = rensa_brukar_data(data["brukare"])
    medarbetare_df = rensa_medarb_data(data["medarbetare"])

    # Read addresses from addresser.txt and assign to brukare
    addresses = read_addresses("Project/data/addresser.txt")
    brukare_df = assign_addresses_to_brukare(brukare_df, addresses)

    # Define time periods and regex patterns
    tid = ["Morgon", "Förmiddag", "Lunch", "Eftermiddag", "Middag", "Tidig kväll", "Sen kväll"]
    regex_tid_mönster = [r'\b[mM]org\b', r'\b[fF]m\b', r'\b[lL]unch\b', r'\b[eE]m\b', r'\b[mM]iddag\b', 
                         r'\b[tT]idig kväll\b', r'\b[sS]en kväll\b']
    
    # Create dictionaries for brukare and medarbetare
    brukare_dag_dict = skapa_brukare_dict(brukare_df, tid, regex_tid_mönster)
    medarbetare_dag_dict = skapa_medarbetare_dict(medarbetare_df, tid, regex_tid_mönster)

    # Create weekly dictionaries for all days
    vecko_dict = create_weekly_dict(brukare_df, medarbetare_df, brukare_dag_dict, medarbetare_dag_dict)

    # Check which medarbetare can visit which brukare and save results
    visit_results = check_visits(medarbetare_dag_dict, brukare_dag_dict)

    # Save or use visit_results as needed for further analysis or optimization

if __name__ == '__main__':
    main()