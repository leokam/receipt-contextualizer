'''
If run as script, process the input list of abbreviated items
'''

from mistralai.client import MistralClient
from mistralai.models.chat_completion import ChatMessage
#from ast import literal_eval

import pandas as pd
import json

import os
from dotenv import load_dotenv
load_dotenv()

api_key = os.getenv('MISTRAL_API_KEY')


# LLM functions
def get_embeddings_by_chunks(data, chunk_size):
    '''
    Returns embeddings for data as a list of arrays.
    '''
    client = MistralClient(api_key)

    chunks = [data[x : x + chunk_size] for x in range(0, len(data), chunk_size)]
    embeddings_response = [
        client.embeddings(model="mistral-embed", input=c) for c in chunks
    ]
    return [d.embedding for e in embeddings_response for d in e.data]

def run_mistral(user_message, model="mistral-medium"):
    """Gets a chat completion response from Mistral API for user_message prompt.

    Args:
        user_message (str): Prompt
        model (str, optional): Model to use, mistral-tiny, mistral-small, mistral-medium. Defaults to "mistral-medium".

    Returns:
        str: message as generated by Mistral.
    """
    client = MistralClient(api_key)
    messages = [
        ChatMessage(role="user", content=user_message)
    ]
    chat_response = client.chat(
        model=model,
        messages=messages,
        temperature=0.5, # default 0.7, lower is more deterministic
        random_seed=42
    )
    return chat_response.choices[0].message.content

def get_rewe_categories():
    """Format the main and subcategories found on the Rewe website for the prompt.
    Each product can be classified with one category. To avoid overlaps, some labels like vegan are excluded.
    Returns:
        str: Formatted categories
    """
    
    # Import product categories as dict w/ key: main category, value: list of subcategories
    path = os.path.dirname(__file__)
    path = os.path.join(path,'data','categories_rewe.json')
    with open(path) as f:
        categories_rewe = json.load(f)

    # Remove certain categories because they are actually labels
    exclude_categories = ['Vegane Vielfalt', 'International', 'Regional']

    for cat in exclude_categories:
        categories_rewe.pop(cat, None)

    # Include new categories needed for items that are not products
    categories_rewe['Sonstige Positionen'] = ['Pfand & Leergut', 'Rabatt & Ermäßigung', 'Kategorie nicht erkannt']

    # String categories together in a formatted string to insert in the prompt
    categories_string = list()
    for main_category in categories_rewe:
        subs_string = '## Unterkategorien\n' + '\n'.join(categories_rewe[main_category])
        categories_string.append(f'# Hauptkategorie\n{main_category}\n{subs_string}\n')
    categories_string = '\n'.join(categories_string)

    return categories_string

def get_prompt(item, categories):
    prompt = (
        f"""
Du bist ein Experte für das Erkennen und Kategorisieren von verkürzten Produktnamen auf Supermarkt-Kassenbons.

Deine Aufgabe ist die folgende:
1. Löse den verkürzten Produktnamen in den Klammern <<< >>> zum vollständigen Produktnamen auf.
2. Ordne das Produkt der Hauptkategorien und der dazugehörige Unterkategorie zu, die das Produkt am besten klassifiziert.

Die möglichen Kategorien sind:

{categories}

Du wirst IN JEDEM FALL nur aus den vordefinierten Kategorien wählen.
Deine Antwort enthält keine Erklärungen oder Anmerkungen. Die Antwort muss in valid JSON formatiert sein.

###
Hier sind einige Beispiele:

Verkürzter Produktname: HAUCHSCHN CURRY
Antwort: productName: Rügenwalder Mühle Veganer Hauchschnitt Typ Hähnchen, categoryMain: Fleisch & Fisch, categorySub: Fleischalternativen

Verkürzter Produktname: GRANATAPEL
Antwort: productName: Granatapfel, category_main: Obst & Gemüse, categorySub: Frisches Obst

Verkürzter Produktname: KASTEN LEER
Antwort: productName: Leergut Kasten, categoryMain: Sonstige Positionen, categorySub: Pfand & Leergut
###

<<<
Verkürzter Produktname: {item}
>>>
"""
    )
    return prompt

def process_abbr_item(item, categories):
    """Completes the shortened item to full product name and categorizes it in a main and sub-category

    Args:
        item (str): The product name as it is on the receipt.

    Returns:
        json: Full product name, main category, subcategory, input item string
    """
    
    prompt = get_prompt(item, categories)

    # Request response from Mixtral
    try:
        print(f'Requesting Mixtral for {item}…')
        message = run_mistral(prompt)
        print('Received response')
    except:
        print('\n\n!!!\n\nError requesting response from Mixtral!\n\nAPI response:')

    # Parse message string to json
    try:
        item_json = json.loads(message)
        item_json['product_abbr'] = item
        print(f"Parses response successfully, {item_json['productName']}")
    except:
        print('\n\n!!!\n\nError parsing Mixtral message, not formatted correctly as JSON!\n\nMessage:')
        print(message)
    
    return item_json

def process_abbr_items_list(item_list, categories):

    list_processed_items = []
    for item in item_list:
        processed_item = process_abbr_item(item, categories)
        list_processed_items.append(processed_item)
    
    return list_processed_items

def process_receipt(receipt_scan_data):
    '''Takes the abbreviated names, queries Mistral for completion for full name, categories, creates embeddings
    
    Args:
        receipt_scan_data (df): DataFrame with columns receipt_id, price, product_abbr
    Returns:
        df: DataFrame with input data, Mistral-inferred data and embeddings
    '''
    # Get abbreviated product names from scan as list
    items_to_process = receipt_scan_data.product_abbr.to_list()

    # Get the categories to use in the prompt
    categories = get_rewe_categories()

    # Prompt Mistral to augment abbreviated items from receipt
    items_processed = process_abbr_items_list(items_to_process, categories)

    # Save Mistral JSONs in a df for concating with embeddings
    items_processed_df = pd.DataFrame(items_processed)

    # Put augmented data for each receipt item in a list for embedding
    product_strings = [" ".join(item.values()) for item in items_processed]

    # Get the embeddings of augmented receipt items
    product_embeddings = get_embeddings_by_chunks(product_strings, 50)

    # Concat embeddings to the processed items df
    items_processed_df['embedding'] = product_embeddings

    # Add information from receipt scan to processed items, price, receipt_id
    items_processed_df = receipt_scan_data.join(items_processed_df.drop('product_abbr', axis=1))
    
    return items_processed_df



def main():
    '''
    For testing
    '''
    # get the items to process
    items_list = [item.strip() for item in input('Input items to process: ').split(',')]
    
    # get categories to categorize items intov
    categories_rewe = get_rewe_categories()

    # process items
    product_list = process_abbr_items_list(items_list, categories_rewe)
    print(product_list)

if __name__=='__main__':
    main()