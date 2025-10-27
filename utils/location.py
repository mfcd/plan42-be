from typing import Literal, get_args

# Define allowed locations
Location = Literal["Apfel", "Birne", "Dattel", "Erdbeere", "Feige", "Granatapfle", "Heidelbeere"]

# Fixed, symmetric distance matrix (in arbitrary units)
distance = {
    ("Apfel", "Birne"): 12,
    ("Apfel", "Dattel"): 25,
    ("Apfel", "Erdbeere"): 18,
    ("Apfel", "Feige"): 30, 
    ("Apfel", "Granatapfle"): 22,
    ("Apfel", "Heidelbeere"): 35,

    ("Birne", "Dattel"): 14,
    ("Birne", "Erdbeere"): 12,
    ("Birne", "Feige"): 28,
    ("Birne", "Granatapfle"): 24,
    ("Birne", "Heidelbeere"): 31,

    ("Dattel", "Erdbeere"): 16,
    ("Dattel", "Feige"): 60,
    ("Dattel", "Granatapfle"): 26,
    ("Dattel", "Heidelbeere"): 27,

    ("Erdbeere", "Feige"): 12,
    ("Erdbeere", "Granatapfle"): 14,
    ("Erdbeere", "Heidelbeere"): 19,

    ("Feige", "Granatapfle"): 11,
    ("Feige", "Heidelbeere"): 15,

    ("Granatapfle", "Heidelbeere"): 17,
}

# Mirror to ensure symmetry
for (i, j), d in list(distance.items()):
    distance[(j, i)] = d

# Add self-distances = 0
for loc in get_args(Location):
    distance[(loc, loc)] = 0