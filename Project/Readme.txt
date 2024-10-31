Krav:
    För att använda programmet måste vissa moduler installeras i python. Dessa är:

    ortools
    pandas
    numpy
    osmnx
    networkx

    Dessa moduler kan istalleras genom att köra kommandot:

    pip install MODULNAMN

    i pythonterminalen där MODULNAMN ersätts med namnet på modulen.

Körning av programmet:
    Programmet körs genom main.py där önskade inställningar för vad som ingår i förmiddags- och eftermiddagsskiften 
    kan anges genom fm_tidsfönster och em_tidsfönster.

    Här kan även koordinaterna för hemtjänstlokalen ändras genom depot_location. 

    När önskade inställningar är angivna kan programmet köras.

    När programmet körs kommer det att fråga efter vilken dag som ska schemaläggas,
    här kan dagarna måndag-fredag anges. 

    Därefter kommer det fråga om det är förmiddagsskift eller eftermiddagsskift som
    ska genereras. Här anges antingen 1 för förmiddag eller 0 för eftermiddag