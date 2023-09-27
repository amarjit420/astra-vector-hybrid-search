# astra-vector-hybrid-search


This is an example of using AstraDB's Vector Similiarity Search (VSS)along with text searching of SAI's Index Analyzer to enable a more powerful hybrid queries searching capabilities.

## Term Search

DataStax Astra DB has launched a new SAI feature that supports index analyzers that allow for matching full or stemmed terms in text columns.  

## Astra DB

The example requires an AstraDB account, which you can signup for free here: https://auth.cloud.datastax.com/ and the creation of Vector DB, and secure connection bundle for the database instance to be downloaded.
Follow the examples here to help setup Astra and get the secure bundle: https://github.com/topics/astradb

## Hybrid code example

### Vector Embeddings

The code will take the following example images and convert them to 256 vector dimension using 'clip-ViT-B-32'

<img width="899" alt="image" src="https://github.com/amarjit420/astra-vector-hybrid-search/assets/80757241/85dff673-f6cf-4ec0-8edd-b2b481d124d6">


### AstraDB Cassandra Tables and Indexes

The following table is created in AstraDB by the code example:

```
CREATE TABLE IF NOT EXISTS ks3.hybridsearch 
( id     int PRIMARY KEY, 
  colour text, 
  description text, 
  item_vector VECTOR<FLOAT, 512>);
```

id = is the unique entry of the image
colour = colour of the image
description = text description of the image
item_vector = embedded vector of the image

for example :

```
{'colour': 'green', 'description': 'round cake edible', 'embedding': [0.3677521347999573, 0.13438430428504944, 0.0669662356376648, ... }
{'colour': 'red', 'description': 'doughnut edible', 'embedding': [0.16388848423957825, 0.16547653079032898, -0.687446117401123, ... }
{'colour': 'red', 'description': 'round cake edible', 'embedding': [0.20938342809677124, 0.008953139185905457, -0.04476819932460785, ... }
```

The index analyzer SAI index created based on the table is:

```
CREATE CUSTOM INDEX ON ks3.hybridsearch(description) USING 'org.apache.cassandra.index.sai.StorageAttachedIndex' WITH OPTIONS = { 
'index_analyzer': '{
	"tokenizer" : {"name" : "standard"},
	"filters" : [{"name" : "porterstem"}]
}'};
```

The vector  SAI index created based on the table used for the ANN is:

```
CREATE CUSTOM INDEX IF NOT EXISTS ON ks3.hybridsearch(item_vector) USING 'StorageAttachedIndex';
```


### Example image files

The example use image that are converted to Vectors, the sample data is in the zipped file image-files.

### ANN Vector only search

In the code example a Vector only search to find the 3 most relevant items matching the string:

```
round cake that's red
```

The response from the Vector ANN search is

```
Query String:  round cake that's red
ANN model provided embeddings for the string: 'search': [-0.06525373458862305, 0.24331393837928772, 0.026663199067115784, -0.026872463524341583, -0.3495931625366211, -0.24691221117973328, -0.23380039632320404, -0.7295491695404053, 0.3060528635978699, -0.3164832592010498, 0.4530841112136841, 0.3531087040901184, -0.10596581548452377, -0.27112826704978943, 0.06920862197875977, 0.25330787897109985, 0.3092903196811676, 0.09679951518774033, -0.36065834760665894, 0.1465529352426529, -0.025295939296483994, 0.3810141682624817, -0.11439329385757446, 0.279330849647522, 0.351209819316864, -0.4630010724067688, -0.2107008397579193, 0.08215729892253876, 0.09898032248020172, -0.09653940796852112, -0.36406463384628296, 0.06989425420761108, -0.04179459810256958, -0.1767721027135849, -0.2358168065547943, 0.11430244147777557, 0.03689675033092499, -0.2486467957496643, 0.416476309299469, 0.10684555768966675, 0.020516008138656616, 0.020283415913581848, 0.05554091930389404, -0.002669617533683777, -0.00805613398551941, 0.06826482713222504, 0.3815672993659973, 0.5780030488967896, -0.36640915274620056, 0.1003582775592804, -0.33170080184936523, -0.38361111283302307, -0.11234325170516968, -0.023725390434265137, -0.029895111918449402, 0.14930664002895355, -0.21050205826759338, ...]

Colour: red
Desc: triangle cake edible
Colour: red
Desc: round cake edible
Colour: red
Desc: doughnut edible
```

<img width="347" alt="image" src="https://github.com/amarjit420/astra-vector-hybrid-search/assets/80757241/ae71cfd4-0084-482f-b209-b696dceb88ca">

Not quite what we were looking for in that order

### index analyzer only search

In the code example a SAI Index Analyzer to find the 3 most relevant items matching the string:

```
Analyzer Match query String: round and edible

Colour: green
Desc: round cake edible
Colour: green
Desc: square cake edible
Colour: red
```

<img width="369" alt="image" src="https://github.com/amarjit420/astra-vector-hybrid-search/assets/80757241/b90cc166-6bc4-4c0d-a0d3-3335658edcab">

As its searching for 'round' and 'edible' words only


### Hybrid Search

If we combine the searches of the ANN search of 'round cake that's red' and the text analyzer for 'red and edible'

```
    query = f"SELECT colour, description FROM {KEYSPACE_NAME}.{TABLE_NAME} WHERE description : 'round' AND description : 'edible' AND colour = 'red'  ORDER BY item_vector ANN OF {text_emb.tolist()} LIMIT 3"
    result = session.execute(query)
```

We get

```
Analyzer Match and ANN together 
Colour: red
Desc: round cake edible
```

<img width="215" alt="image" src="https://github.com/amarjit420/astra-vector-hybrid-search/assets/80757241/c603c7ac-af5e-4397-90ad-25a9d6274681">

