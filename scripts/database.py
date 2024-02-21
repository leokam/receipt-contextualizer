from venv import create
import psycopg2
from psycopg2.extras import execute_values
from pgvector.psycopg2 import register_vector
from psycopg2 import sql

import pandas as pd
import numpy as np

# Database connection

def connect_cursor():
    '''Connects to postgres, returns (connection, cursor)'''
    try:
        conn = psycopg2.connect(
            host="localhost",
            database="receipts",
            user="postgres",
            password='postgres'
        )
        cur = conn.cursor()
        # Register the vector type with psycopg2
        register_vector(conn)
    except:
        print('Error connecting to database')
    return (conn, cur)

# Setup
def setup_vector(conn, cur):
    # Install pgvector
    cur.execute("CREATE EXTENSION IF NOT EXISTS vector");
    conn.commit()

def create_table(table, conn, cur):
    '''Create either receipts or rewe database'''

    if table == 'receipts':
        table_create_command = """
            CREATE TABLE receipts (
                        id bigserial primary key, 
                        receipt_id text,
                        price float,
                        product_abbr text,
                        product_name text,
                        category_main text,
                        category_sub text,
                        embedding vector(1024)
                        );
                        """
        cur.execute(table_create_command)
        cur.close()
        conn.commit()
        
        print(f'Created table {table}')

    if table == 'rewe':
        table_create_command = """
            CREATE TABLE rewe (
                        id bigserial primary key, 
                        name text,
                        price float,
                        category text,
                        embedding vector(1024)
                        );
                        """
        cur.execute(table_create_command)
        cur.close()
        conn.commit()

        print(f'Created table {table}')

    else:
        print(f'Table format not found: choose either receipts/rewe')

def setup_rewe_table(conn, cur):
    '''Fills rewe table with store products, embeddings'''
    df_rewe = pd.read_csv('../data/name_embeds_incl_special_items_no_context.csv', index_col=0)
    data_list = [(row['name'], row['price'], row['category'], row['embeddings']) for _, row in df_rewe.iterrows()]
    execute_values(cur, "INSERT INTO rewe (name, price, category, embedding) VALUES %s", data_list)
    conn.commit()

# Write to database
def insert_receipt_data(processed_receipt_data, conn, cur):
    '''Writes a receipt df into receipts database.'''
    
    # Prepare data to insert to psql
    data_list = [(
        row['receipt_id'], 
        row['price'], 
        row['product_abbr'], 
        row['productName'], 
        row['categoryMain'], 
        row['categorySub'], 
        np.array(row['embedding'])
        ) for _, row in processed_receipt_data.iterrows()]
    
    # SQL query
    execute_values(cur, "INSERT INTO receipts (receipt_id, price, product_abbr, product_name, category_main, category_sub, embedding) VALUES %s", data_list)
    conn.commit()
    print('Wrote in database.')

# Retrieve from database
def get_receipt_data(conn, cur):
    '''Returns all receipt data in database as DataFrame.'''

    # SQL query
    cur.execute("SELECT * FROM receipts;")
    records = cur.fetchall()
    conn.close()

    # Format table with column names
    column_names = [x.strip() for x in 'id_pk, receipt_id, price, product_abbr, \
                    product_name, category_main, category_sub, embedding'.split(',')]
    df = pd.DataFrame(records, columns=column_names)

    return df

# Query database
def get_closest(query_embedding, n_closest, table, conn, cur):
    '''Performs semantic search on user query either in receipts or rewe table.'''

    # Format embedding str as array
    # Embedding function returns a list, get the first element of list
    query_embedding_array = np.array(query_embedding[0])

    # KNN nearest neighbors by L2 distance <-> operator
    # Also supports inner product (<#>) and cosine distance (<=>)

    cur.execute(
        sql.SQL("SELECT * FROM {} ORDER BY embedding <=> %s LIMIT %s")\
            .format(sql.Identifier(table)), 
            (query_embedding_array, n_closest))
    records = cur.fetchall()
    conn.close()

    # Format results with column names
    if table == 'receipts':
        column_names = [x.strip() for x in 'id_pk, receipt_id, price, product_abbr, \
                        product_name, category_main, category_sub, embedding'.split(',')]
        df = pd.DataFrame(records, columns=column_names)
    if table == 'rewe':
        df = pd.DataFrame(records, columns=['id', 'name', 'price', 'category', 'embedding'])

    return df

if __name__=='__main__':
    '''Run setup
    
    Installs vector extension to postgres
    Sets up receipts table
    Sets up rewe table
    Fill rewe table with products and embeddings'''
    
    conn, cur = connect_cursor()
    setup_vector(conn, cur)
    create_table('receipts', conn, cur)
    create_table('rewe', conn, cur)
    setup_rewe_table(conn, cur)

