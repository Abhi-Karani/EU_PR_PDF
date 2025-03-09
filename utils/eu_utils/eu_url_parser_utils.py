import requests
import copy
from bs4 import BeautifulSoup
import backoff
import re
import tiktoken
import utils.eu_utils.eu_common_utils as eu_common_utils
from service.logger.logger import get_logger
logger = get_logger("eu_url_parser_utils")



# Define the exceptions to retry on
retriable_errors = (requests.exceptions.RequestException, Exception)
def reset_connection_if_connection_issue(details):
    logger.info(f"Backing off {details['wait']:0.1f} seconds after {details['tries']} tries. Exception: {details['exception']}")


@backoff.on_exception(backoff.constant,
    retriable_errors,
    max_tries=3,
    on_backoff=reset_connection_if_connection_issue,
    interval=10)
def get_html_content(url):
    """ 
        input: url
        outputs: the full HTML content of press Release, full HTML of the url 
    """
    url_response = requests.get(url)
    if url_response.status_code == 200:
        html_content= url_response.text
        soup = BeautifulSoup(html_content, 'html.parser')
        try:
            content = soup.find('div',{'id':"PP4Contents"})
            temp = content.text #this will throws error if pp4contents not there, find returns none if pp4 not found, nonetype has no text
            return content, soup
        except Exception as e:
            logger.error(f"There is no PP4Contents Tab in the content will not be able to parse the document {content}") #if !PP4 end program here
            raise eu_common_utils.retryException(f"""Failed to retrieve PP4Contents content from the web page {url} with status code {url_response.status_code}, 
                            exception {e}""")
    else:
        raise Exception(f"Failed to retrieve the web page {url} with status code {url_response.status_code}")

def get_title(url):
    """ 
        input: url
        outputs: the full HTML content of press Release, full HTML of the url 
    """
    url_response = requests.get(url)
    if url_response.status_code == 200:
        html_content= url_response.text
        soup = BeautifulSoup(html_content, 'html.parser')
        try:
            content = soup.find('p',{'id':"title"})
            return content.text
        except Exception as e:
            raise Exception(f"""Failed to retrieve Title from the web page {url} with status code {url_response.status_code}, 
                            exception {e}""")
    else:
        raise Exception(f"Failed to retrieve the web page {url} with status code {url_response.status_code}")

def get_category(content):
    """
        input: content
        output: category of the content, if no category returns Category 0
    """
    has_annex = get_has_annex(content)
    has_oj_tables = get_has_oj_tables(content)
    if has_annex and has_oj_tables:
        return "Category 7"
    elif has_annex and not has_oj_tables:
        return "Category 5"
    elif not has_annex and not has_oj_tables:
        return "Category 1"
    else:
        return "Category 0"
    
def get_annex_from_content(soup):
    """
        input: soup,(html content)
        output: Annexs (html formatted)
    """
    try:
        relevant_containers = []
    # Find all divs with the class 'eli-container'
        eli_containers = soup.find_all("div", class_="eli-container")
        # logger.info(len(eli_containers))

        if len(eli_containers) != 0:

            # Iterate through these containers
            for container in eli_containers:
                # logger.info(type(container))

                # Check if the first element within the container is the 'p' tag
                first_child = container.find(recursive=False)  # Get the immediate first child

                # Ensure it's a 'p' tag with the class 'oj-doc-ti' and contains 'ANNEX'
                if first_child and first_child.name == "p" and "oj-doc-ti" in first_child.get("class", []) and "ANNEX" in first_child.get_text(strip=True):
                    relevant_html = container.prettify()
                    relevant_containers.append(container)
            logger.info("used the eli-container contains ANNEX logic")
            return relevant_containers

        elif len(eli_containers) == 0:
            
            annexes = soup.find_all('div', {'id': re.compile(r'^(L_|LI20)')})

            if len(annexes) != 0: 
                logger.info("used the REGEX ANNEX logic")
                return annexes
            else:
                return []
    except Exception as E:
        raise Exception(f"Error in get_annex_from_content: {E}")

def if_current_row_there_then_append_else_independent_row(current_row, row):
    try:
        if current_row:
            current_row = current_row+str(row)
        else:
            current_row = str(row)
        return current_row
    except Exception as E:
        raise Exception(f"Error in if_current_row_there_then_append_else_independent_row for current_row: {current_row} and row: {row} and Error: {E}")

def has_oj_header(row):
    para = row.find_all('p', class_='oj-tbl-hdr')
    if para:
        return True
    else:
        return False

def get_rows_from_list_of_tables(oj_tables):
    try:
        oj_table_rows = []
        # Remove text content belonging to tables
        for table in oj_tables:
            rows = table.find_all('tr', class_='oj-table')
            if has_oj_header(rows[0]):
                table_header = rows[0]
            else:
                table_header = ""
            print(f"The length of rows in this table is {len(rows)}")
            if not rows:
                continue
            max_columns = max(len(row.find_all('td', recursive=False)) for row in rows)
                
            processed_rows = []
            current_row = ""
            processed_rows = []
            for row in rows:
                columns = row.find_all('td')
                if columns:
                    if len(columns) < max_columns:
                        current_row = if_current_row_there_then_append_else_independent_row(current_row, row)
                    else:
                        if columns[0].get_text(strip=True) == "":  
                            current_row = if_current_row_there_then_append_else_independent_row(current_row, row)
                        else:
                            if current_row:
                                # print(f"the current row is {current_row}")
                                refined_row = str(table_header)+current_row
                                processed_rows.append(refined_row)
                            current_row = str(row)
                else:
                    current_row = if_current_row_there_then_append_else_independent_row(current_row, row)
            if current_row:
                processed_rows.append(current_row)
            oj_table_rows.extend(processed_rows)
        return oj_table_rows
    except Exception as E:
        raise Exception(f"Error in get_rows_from_list_of_tables for oj_tables: {oj_tables} and error: {E}")

def split_annex_into_text_tables_rows(annex):
    try:
        content = []
        # Extract all text from the document
        all_text = str(annex)
        
        # Find all tables
        oj_tables = annex.find_all('table', {"class":'oj-table'})
        rows = get_rows_from_list_of_tables(oj_tables)

        for table in oj_tables:
            all_text = all_text.replace(str(table), '') 

        for row in rows:
            single_element_in_content_dictionary = {"row": row}
            content.append(single_element_in_content_dictionary)
        
        single_element_in_content_dictionary = {"text": all_text}
        content.append(single_element_in_content_dictionary)
        return content, all_text, oj_tables, rows
    except Exception as E:
        raise Exception(f"Error in split_annex_into_text_tables_rows for annex: {annex} and error: {E}")

def get_has_annex(content):
    annexs = get_annex_from_content(content)
    if annexs:
        return True
    else:
        return False

def get_has_oj_tables(content):
    ojTables = content.find_all('table', {"class":'oj-table'})
    if ojTables:
        return True
    else:
        return False

def perform_token_check(string: str, model: str) -> int:
    """
        input: string, model
        output: num of tokens in the string, raises exception if the input exceeds the token limit
    """
    try:
        encoding = tiktoken.encoding_for_model(model)
    except KeyError:
        logger.error("Warning: model not found. Using cl100k_base encoding.")
        encoding = tiktoken.get_encoding("cl100k_base")
    
    num_tokens = len(encoding.encode(string))
    logger.info(f"URL has {num_tokens} tokens")
    if num_tokens > 110011: #128000-16384(output tokens) - 1605(prompt tokens for subsequent prompt(largest prompt)+datapointsextractor )
        raise Exception(f"input tokens greater that 110011")
    return num_tokens

def get_html_text_oj_tables_seperate(fullcontenthtml):  
    """
        input: html soup
        output: split into contents[annex-wise(oj-tables, text outside oj-tables)]
    """
    try:
        content_final = []
        annexs = get_annex_from_content(fullcontenthtml)
        image_links = adjust_for_images(annexs)
        try:
            logger.info(f"number of annexs is: {len(annexs)}")
            for i in range(len(annexs)):
                content,texts,oj_tables,_ = split_annex_into_text_tables_rows(annexs[i])
                logger.info(f"Annex number: {i}, oj_tables: {len(oj_tables)}, text: {len(texts)}, content_length: {len(content)}")
                content_final.extend(content)
        except Exception as e:
            logger.error(f"Exception occured while trying to chunck the annexs: {e}")
            raise Exception(f"Exception occured while trying to chunck the annexs, for annex_number {i} and error: {e}")
        
        logger.info(f"The total size for content is: {len(content_final)}")

    except Exception as e:
        logger.error(f"Error in parsing annexs: {e}")
        raise Exception(f"Error in parsing annexs: {e}")
    return content_final,fullcontenthtml, image_links

def adjust_for_images(annexs):
    image_links = {}
    image_count = 1
    try:
        for annex in annexs:
            imgs = annex.find_all('img')
            try:
                if imgs:
                    logger.info("There are images in this annex")
                    for img in imgs:
                        replacement_text = f"image_{image_count}"
                        image_links[replacement_text] = img['src']  # Save the image link in the dictionary 
                        img.replace_with(replacement_text)
                        image_count += 1
            except Exception as E:
                #Note since we are not raising it, what this error might lead to is incomplete image data capture.
                logger.error(f"There was some error while trying to adjust for images: {E}")
        return image_links
    except Exception as E:
        #todo review needed
        #Note if there is some issue we send the image_links which can be an empty dictionary or incomplete data capture
        logger.error(f"Error in adjust_for_images: {E}")
        return image_links 
    
def find_text_outside_ojtables_and_ojtables(annex): #seperates the annex into oj_tables and all the text outside the oj_tables
    try:
        content = []
        # Extract all text from the document
        all_text = str(annex)
        # Find all tables
        oj_tables = annex.find_all('table', {"class":'oj-table'})

        # Remove text content belonging to tables
        for table in oj_tables:
            all_text = all_text.replace(str(table), '')
        content.extend(oj_tables)
        content.append(all_text)
        return content, all_text,oj_tables
    except Exception as E:
        raise Exception(f"Error in find_text_outside_ojtables_and_ojtables error: {E} and where annex: {annex}")
    
def remove_irrelevant_columns_from_tables_in_annex(annex):
    try:
        oj_tables = annex.find_all('table', {"class":'oj-table'})
        for table in oj_tables:
            rows = table.find_all('tr', class_='oj-table')
            for row in rows:
                    columns = row.find_all('td', class_='oj-table')
                    for i in range(len(columns)):
                        if i > 1:
                            columns[i].replace_with(" ")
        return None
    except Exception as E:
        logger.error(f"Error in remove_irrelevant_columns_from_tables_in_annex: {E} for annex: {annex}")
        return annex

def format_vertical_bar_table(headers, data):
    # Create header row
    header_row = '| ' + ' | '.join(headers) + ' |'
    
    # Create separator row
    separator_row = '|-' + '-|-'.join(['-' * len(header) for header in headers]) + '-|'
    
    # Create data rows
    data_rows = []
    for row in data:
        data_rows.append('| ' + ' | '.join(row) + ' |')
    
    # Combine all parts into final table format
    return '\n'.join([header_row, separator_row] + data_rows)

def vertical_line_formatting_for_tables(annex):
    try:
        oj_tables = annex.find_all('table', {"class":'oj-table'})
        for table in oj_tables:
            rows = table.find_all('tr', class_='oj-table')
            data = []
            if has_oj_header(rows[0]):
                headers = [header.get_text(strip=True) for header in rows[0].find_all('p')]
                for row in rows[1:]:
                    cols = row.find_all('td')
                    data.append([col.get_text(strip=True) for col in cols])
                table_formatted = format_vertical_bar_table(headers, data)
                table.replace_with("\n"+table_formatted+"\n")
    except Exception as E:
        logger.error(f"Error in vertical_line_formatting_for_tables: {E} for annex: {annex}")
        return annex

def normalize_content(full_content_html):
    try:
        annexs = get_annex_from_content(full_content_html)
        for i in range(len(annexs)):
            _ = remove_irrelevant_columns_from_tables_in_annex(annexs[i])
            _ = vertical_line_formatting_for_tables(annexs[i])
        full_content_without_html = full_content_html.get_text(strip = True)
        return full_content_without_html
    except Exception as E:
        logger.error(f"Error in normalize_content: {E}")
        return full_content_html
    
def copy_html_soup(full_content_html):
    copied_html = BeautifulSoup(str(full_content_html), 'html.parser')
    return copied_html

def remove_the_header_row_from_a_bs_row(bs_row):
    try:
        rows = bs_row.find_all('tr', class_='oj-table')
        table_header = ""
        if has_oj_header(rows[0]):
            table_header = rows[0]
        string_bs_row = str(bs_row)
        string_output_row = string_bs_row.replace(str(table_header), '') 
        bs_output_row = BeautifulSoup(string_output_row, 'html.parser')
        return bs_output_row
    except Exception as E:
        logger.error(f"Error in remove_the_header_row_from_a_row for {bs_row} and error: {E}")
        return bs_row