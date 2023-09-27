import os
from sentence_transformers import SentenceTransformer
import numpy as np
from PIL import Image
from cassandra.cluster import Cluster
from cassandra.auth import PlainTextAuthProvider


PATH_TO_BUNDLE      = "<location to  secure_connect_bundle.zip"
ASTRA_CLIENT_ID     = 'Your Astra DB client ID'
ASTRA_CLIENT_SECRET = 'Your Astra DB ASTRA_CLIENT_SECRET'
KEYSPACE_NAME       = 'ks3'
TABLE_NAME          = 'hybridsearch'
INPUT_PATH          = "<location to /image-files/>"

def main():

    lst = []

    img_model = SentenceTransformer('clip-ViT-B-32')

    # Iterate over each file in the directory
    for filename in os.listdir(INPUT_PATH):
        # Check if the file is a .jpg image
        if filename.endswith('.jpg'):
            image = Image.open(INPUT_PATH + filename)

            # Extract file name without extension
            file_name_without_extension = os.path.splitext(filename)[0]

            print(f"Processing image: {file_name_without_extension}")

            doc = {}
            embedding = image_embedding(image, img_model)
            formatted_string   = file_name_without_extension.split("_")
            doc['colour']      = formatted_string[0]
            doc['description'] = ' '.join(formatted_string[1:])
            doc['embedding']   = embedding.tolist()

            lst.append(doc)
            print(doc)

    # Replace these values with the path to your secure connect bundle and the database credentials
    SECURE_CONNECT_BUNDLE_PATH = os.path.join(os.path.dirname(__file__), PATH_TO_BUNDLE)

    # Connect to the database
    cloud_config = {'secure_connect_bundle': SECURE_CONNECT_BUNDLE_PATH}
    auth_provider = PlainTextAuthProvider(ASTRA_CLIENT_ID, ASTRA_CLIENT_SECRET)
    cluster = Cluster(cloud=cloud_config, auth_provider=auth_provider)
    session = cluster.connect()

    print(f"Creating table {TABLE_NAME} in keyspace {KEYSPACE_NAME}")


    session.execute(
            f"CREATE TABLE IF NOT EXISTS {KEYSPACE_NAME}.{TABLE_NAME} (id int PRIMARY KEY, colour TEXT, description TEXT, item_vector VECTOR<FLOAT, 512>)")

    print(f"Creating indexes  on table {TABLE_NAME} ")
    session.execute(
    f"CREATE CUSTOM INDEX IF NOT EXISTS ON {KEYSPACE_NAME}.{TABLE_NAME}(item_vector) USING 'StorageAttachedIndex'")

    session.execute(
        f"CREATE CUSTOM INDEX IF NOT EXISTS ON {KEYSPACE_NAME}.{TABLE_NAME}(colour) USING 'StorageAttachedIndex'")

    print(f"Creating SAI index analyser  on table {TABLE_NAME} ")
    session.execute(
    f"CREATE CUSTOM INDEX IF NOT EXISTS ON {KEYSPACE_NAME}.{TABLE_NAME}(description) USING 'StorageAttachedIndex' ")

    print(f"Truncate table {TABLE_NAME} in keyspace {KEYSPACE_NAME}")
    session.execute(f"TRUNCATE TABLE {KEYSPACE_NAME}.{TABLE_NAME}")

    count = 0

    for data in lst:
        count += 1
        print(f"Data #{count}:")
        image_colour = data["colour"]
        image_description = data["description"]
        image_embeddings = data["embedding"]

        # Perform operations with the data
        print("Image Colour:", image_colour)
        print("Image Desc:", image_description)
        print("Image Embedding (First 20 characters):", str(image_embeddings)[:50])
        print()

        # Insert the data into the table
        session.execute(
            f"INSERT INTO {KEYSPACE_NAME}.{TABLE_NAME} (id, colour, description, item_vector) VALUES (%s, %s, %s, %s)",
            (count, image_colour, image_description, image_embeddings))

    print("Total number of records inserted :", count)


    vector_query_str = "round cake that's red"
    print("Query String: ", vector_query_str)
    text_emb = img_model.encode(vector_query_str)
    print(f"ANN model provided embeddings for the string: 'search': {text_emb.tolist()}")


    # Retrieve the nearest matching image from the database
    query = f"SELECT colour, description FROM {KEYSPACE_NAME}.{TABLE_NAME} ORDER BY item_vector ANN OF {text_emb.tolist()} LIMIT 3"
    result = session.execute(query)

    for row in result:
        print("Colour:", row.colour)
        print("Desc:", row.description)


    print("Analyzer Match query String: round and edible")

    query = f"SELECT colour, description FROM {KEYSPACE_NAME}.{TABLE_NAME} WHERE description : 'round' AND description : 'edible'  LIMIT 3"
    result = session.execute(query)

    for row in result:
        print("Colour:", row.colour)
        print("Desc:", row.description)

    print("Analyzer Match and ANN together ")

    query = f"SELECT colour, description FROM {KEYSPACE_NAME}.{TABLE_NAME} WHERE description : 'round' AND description : 'edible' AND colour = 'red'  ORDER BY item_vector ANN OF {text_emb.tolist()} LIMIT 3"
    result = session.execute(query)

    for row in result:
        print("Colour:", row.colour)
        print("Desc:", row.description)


    # Close the connection
    session.shutdown()
    cluster.shutdown()



def image_embedding(image, model):
    return model.encode(image)


if __name__ == '__main__':
    main()