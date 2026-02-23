import csv
import re
import os

def parse_sql_values(sql_file):
    with open(sql_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Extract the VALUES part
    values_match = re.search(r'VALUES\s+(.*);', content, re.DOTALL | re.IGNORECASE)
    if not values_match:
        return []
        
    values_str = values_match.group(1).strip()
    
    # Very simple parser for (val1, val2, ...), (val1, val2, ...)
    # This works because we know our SQL structure is clean now
    rows = []
    # Split by ),\n( or ), ( to get individual rows
    # We remove the leading ( and trailing )
    raw_rows = re.split(r'\s*\)\s*,\s*\(\s*', values_str.strip()[1:-1])
    
    for raw_row in raw_rows:
        # Split by comma but respect single quotes
        # This is a bit tricky, but since we know our data, we can use a regex
        # Or even better, just use csv.reader on a single line
        reader = csv.reader([raw_row], quotechar="'", skipinitialspace=True)
        row = next(reader)
        # Convert 'NULL' strings to empty or actual None
        row = [None if col == 'NULL' else col for col in row]
        rows.append(row)
    
    return rows

def generate_csvs():
    output_dir = r'd:\learning\aml\db\csv'
    os.makedirs(output_dir, exist_ok=True)
    
    # 1. Sanctions List
    sanctions_rows = parse_sql_values(r'd:\learning\aml\db\sanctions_data.sql')
    sanctions_headers = ['entity_name', 'entity_type', 'program', 'list_type', 'country', 'entity_address', 'tax_id', 'remarks']
    with open(os.path.join(output_dir, 'sanctions_list.csv'), 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(sanctions_headers)
        writer.writerows(sanctions_rows)
    print(f"Created {os.path.join(output_dir, 'sanctions_list.csv')}")

    # 2. Entity Verification
    verification_rows = parse_sql_values(r'd:\learning\aml\db\verification_data.sql')
    verification_headers = ['lei_number', 'company_name', 'entity_type', 'registered_address', 'country', 'ein_number', 'dba_name']
    with open(os.path.join(output_dir, 'entity_verification.csv'), 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(verification_headers)
        writer.writerows(verification_rows)
    print(f"Created {os.path.join(output_dir, 'entity_verification.csv')}")

if __name__ == "__main__":
    generate_csvs()
