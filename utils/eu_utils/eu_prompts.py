context_call= """ You are a sanctions expert at a bank. you will be given a document related to sanctions and \
    your task will be to extract what object is being affected by the sanction and the context.
    Definitions: 
        1. object: the "table"/"enterprise"/"person" that the sanction is affecting, as per the given document
        2. context: the complete action of what is happening to the object, exactly as it is given in the document
                
    Guidelines: 
        - If an annex is being replaced by a table, then the table is the object
        - If any individual is being deleted then the individual is the object
    
    Give the output as a json object:
        as "object":"context
        for example: 
            {
                "Table 1":"under the heading ‘I. Persons and entities involved in nuclear or ballistic missile activities and persons and entities providing support to the Government of Iran.’, the following entries replace the corresponding entries in the list set out under the subheading ‘B. Entities’",
                "entries 59 (concerning Marou Sanat (a.k.a. Mohandesi Tarh Va Toseh Maro Sanat Company))":"in the list headed ‘I. Persons and entities involved in nuclear or ballistic missile activities and persons and entities providing support to the Government of Iran.’, under the subheading ‘B. Entities’, are deleted,"
                //extract all the objects present in the given document and their corresponding contexts
            }
"""

name_extractor_prompt_sub= """
Given the content above, please extract the name and the corresponding change_type of all the sanctioned entities and individuals \
    given in the content after the last_entry_extracted.


Give the output in format of name:change_type_flag.

Definitions for name and change_type_flag are:\
["name": 'Full name of the sanctioned individual/entity as per the given content.
            Ensure that the full name includes titles (such as Mr., Dr., General, Colonel, Major, etc.).
            Also ensure that the full name does NOT include aliases which are mentioned inside parentheses.
    
            Please refer to the following examples to understand the format in which the provided content may have aliases:
            Examples:
            1. "Dimitriy (Dimitry, Dmitri, Dmitry) Valerievich UTKIN" -> Name: "Dimitriy Valerievich UTKIN"
            2. "Ekaterina Vasilyevna TERESHCHENKO Ekaterina Vasilievna TERESHCHENKO" -> Name: "Ekaterina Vasilyevna TERESHCHENKO"
            3. "Elena Valerievna KRAVCHENKO / Elena Valeryevna KRAVCHENKO" -> Name: "Elena Valerievna KRAVCHENKO"
            4. "Mikhail Vladimirovich DEGTYARYOV/DEGTYAREV" -> Name: "Mikhail Vladimirovich DEGTYARYOV"
            5. "yanina valeryevna okhota, kozhemyako" -> Name: "yanina valeryevna okhota"
            6. "Khatiba Imam Al-Bukhari (KIB)" -> Name: "Khatiba Imam Al-Bukhari"
            7. "Anant Kiran Gupta (Goopta)" -> Name: "Anant Kiran Gupta"',
"change_type_flag": "takes the value 'Addition', or 'Deletion', or 'Amendment' respectively for the change of type \
        addition/listing, or deletion/de-listing, or amendment (i.e. any changes) to sanctioned individual/entity as per the provided content"]

bodies include sanctioned individuals and entities
[for example consider the following bodies are present in the document in this given order \
Annex I

part A
person_1
person_8
person_3
person_2
person_4
person_120
person_5
entity_3
entity_4
entity_1
//more bodies
and the last_entry_extracted is person_3 you have to extract the bodies in the same order\
      in which it is given in the content AFTER the last_entry_extracted i.e. 
person_2
person_4
person_120
person_5
entity_3
entity_4
entity_1
//extract ALL the remaining bodies
] 

Give the output in json format
{
    "result":
        [   
            {
                "Alexey Yevgenevich FILATOV": "Addition",
                "Hadi ZAHOURIAN": "Amendment",
                \\ add all the entries as per the content
            }
        ]
}

DO NOT RETURN ANY ADDITIONAL TEXT (OR SPACES) AROUND THE JSON OUTPUT.

**Treat Vessels as ENTITIES**
If the provided content does not mention detailed information about any change (addition/amendment/delition) 
for any sanctioned individuals or entities at all, then return only NONE string as the output.
AGAIN, DO NOT RETURN ANY ADDITIONAL TEXT (OR SPACES) AROUND THE NONE STRING.
"""

json_format_expected_from_output = """{

    "result":
        [
            {
                "entityType": "Individual",
                "name":"Suhayl HASSAN"
                "name_info": "Suhayl (a.k.a. Sohail, Suhail, Suheil) HASSAN (a.k.a. Hasan, al-Hasan, al-Hassan) known as “The Tiger” (a.k.a. al-Nimr)"
                \\add more fields
            },
            {
                "entityType": "Individual",
                "name":"Dr. Mohammad AL SAYED"
                "name_info": "	Dr. Mohammad (Image 70) (a.k.a. Mohamed, Muhammad, Mohammed) Abdul-Sattar (Image 71) (a.k.a. Abd al-Sattar) AL SAYED (Image 72) (a.k.a. Al Sayyed)
                \\add more fields
            }
            \\ add more entries as per the content
        ]

}
Note: an IMO number is assigned only to a VESSEL
"""


#        **IF THE KEYWORD "ASSOCIATED" INDIVIDUAL/ENTITIES IS GIVEN, DONOT TREAT THEM AS SEPERATE RECORDS**

#**if a record has explicit mention of *associated individuals/entities* do not consider the associated bodies as seperate records**

# **IF A RECORD EXPLICITLY MENTIONS ASSOCIATED INDIVIDUALS OR ENTITIES, DO NOT TREAT THEM AS SEPARATE RECORDS.**

#         **DO NOT CONSIDER ASSOCIATED INDIVIDUALS/ENTITIES AS SEPERATE RECORD IF THEY ARE EXPLICITLY MENTIONED AS IDENTIFYING INFORMATION FOR A RECORD**

# **DO NOT CONSIDER ASSOCIATED INDIVIDUALS/ENTITIES AS SEPERATE RECORD IF THEY ARE EXPLICITLY MENTIONED UNDER IDENTIFYINGC INFORMATION FOR A RECORD**

#**INCASE ASSOCIATED INDIVIDUALS/ENTITIES ARE MENTIONED FOR A RECORD, EACH OF THOSE INDIVIDUALS/ENTITIES ARE SUPPOSED TO \
            # BE CONSIDERED AS SEPERATE RECORDS *ONLY IF* DATE OF LISTING IS MENTIONED EXPLICITLY FOR EACH OF THEM **

data_point_extractor_system_prompt_1 = f"""
Use the given content to extract all (or as many of them as present in the content) the data points for\
      all of the sanctioned individuals and entities as per the provided content.

All the data_points are supposed to be extracted, as per the given content ONLY.

DO NOT SUMMARIZE ANY OF THE INFORMATION, but extract it as it is.

First,
In case of additions and amendments(changes) and deletions of individuals/entities, all the individuals or entities (added or amended or deleted) \
would be in a list format or in a tabular format, in the provided content . \
But the lists or tables for individuals and entities will always be separate from each other. 
Thus DO NOT CONFUSE THE ENDS AND BEGINNINGS of separate lists or tables, for separate entityType (i.e. individual/entity)

Next, 
In case of any deletions of individuals/entities, either one/many of individuals/entities could be deleted or \
the entire annex itself could be deleted. Please extract the information in both these cases (while adhering to the \
below-mentioned JSON format).

Finally, 
MAKE SURE TO generate response in the following JSON format: For example
{json_format_expected_from_output}
DO NOT RETURN ANY ADDITIONAL TEXT (OR SPACES) APART FROM THE JSON OBJECT IN OUTPUT.

If one of the data points is not present in the content for any of the individual/entity, then we return NA string as the value for the key of that data point.

On the other hand, if the provided content does not mention detailed information about any change (addition/amendment/delition) 
for any sanctioned individuals or entities at all, then return only NONE string as the output.

if for any sanctioned body (individual and entity), there are associated Individuals or Entities, DO NOT consider the associated bodies as seperate records
AGAIN, DO NOT RETURN ANY ADDITIONAL TEXT (OR SPACES) AROUND THE NONE STRING.

"""

#             Furthermore, in case of a deletion, if all the individuals/entities in an annex are deleted, then return "ALL" as the full name.""",
#Furthermore, if no name for an individual/entity is given then return "ALL" as the full name.""",
data_points_extractor = {
    "entityType": "Individual, Entity or Vessel; determined based on heading/description accompanying the details of the individual/entity/vessel or the list \
        of individuals/entities/vessels or the table of individuals/entities/vessels, as per the provided content",
    "name": """Full name of the sanctioned individual/entity as per the given content.
            Ensure that the full name includes titles (such as Mr., Dr., General, Colonel, Major, etc.).
            Also ensure that the full name does NOT include aliases which are mentioned inside parentheses.
    
            Please refer to the following examples to understand the format in which the provided content may have aliases:
            Examples:
            1. "Dimitriy (Dimitry, Dmitri, Dmitry) Valerievich UTKIN" -> Name: "Dimitriy Valerievich UTKIN"
            2. "Ekaterina Vasilyevna TERESHCHENKO Ekaterina Vasilievna TERESHCHENKO" -> Name: "Ekaterina Vasilyevna TERESHCHENKO"
            3. "Elena Valerievna KRAVCHENKO / Elena Valeryevna KRAVCHENKO" -> Name: "Elena Valerievna KRAVCHENKO"
            4. "Mikhail Vladimirovich DEGTYARYOV/DEGTYAREV" -> Name: "Mikhail Vladimirovich DEGTYARYOV"
            5. "yanina valeryevna okhota, kozhemyako" -> Name: "yanina valeryevna okhota"
            6. "Khatiba Imam Al-Bukhari (KIB)" -> Name: "Khatiba Imam Al-Bukhari"
            7. "Anant Kiran Gupta (Goopta)" -> Name: "Anant Kiran Gupta"
             
            Furthermore, if no name for an individual/entity is given then return "ALL" as the full name.""",
    "name_info":"""The complete information about *only* the name (latin script names and non latin script names) of an individual \
        and an entity *exactly as given in the document*, including any "names", "aliases", "a.k.a", "formerly known as",\
            "also known as" ,"orginal script names", "original script aliases", "maiden names", "names in all the languages" etc. 
            as per the given content, *Ensure accuracy and do not infer or add any information beyond the provided content*
            """,
    "designation": "array of strings of designations held by the sanctioned individual/entity as per the provided content; if not present, return 'NA'",
    "placeOfBirth": "array of strings of place of birth(s) of the sanctioned individual/entity as per the provided content; if not present, return 'NA'",
    "dateOfBirth": "array of strings of dates of birth(s) of the sanctioned individual/entity as per the provided content; if not present, return 'NA'",
    
    "nationality_Country_Name": """array of strings of names of all the Countries where the sanctioned individual \
        has a nationality, as mentioned explicitly in the given content, by phrases such as \
            'national of [Country(s)]' or '[Country(s)] national' or 'nationality [Country(s)]' 
        Do not infer nationality from birth, citizenship or any other identifiers,\
            Ensure to return the names of the countries for example (Australia instead of Australian); 
        if nationality is not given explicitly in the provided content, return 'NA'""",
    
    "citizenship_Country_Name":"""array of strings of names of all the Countries where the sanctioned individual \
        holds citizenship as mentioned explicitly in the given content. by phrases such as \
            "citizen of [Country(s)]" or "[Country(s)] citizen" or "citizenship [Country(s)]" 
        Do not infer citizenship from birth,nationality or any other identifiers. \
            Ensure to return the names of the countries for example (Australia instead of Australian); 
        if citizenship is not given explicitly in the provided content, return 'NA'""",
    
    "gender": "gender of the sanctioned individual as per the content; if not present, return 'NA'",
    "idDetails":"""A list of dictionaries consisting of \
        idType (type of the concerned id as given in the content), \
        idValue (The alpha-numeric code of the concerned id as given in the content), \
        id_remarks(any other information about the concerned id as per the given content) \
            of all the ids for an individual and/or entity, as per the provided content \
        Ensure that all the ids present throughout the provided content, for the given individual/entity are extracted in this list.
 
        For example \
            [{"idType":"Registration number",
             "idValue":"123456789",
             "id_remarks":"BVL"},
             {"idType":"Passport number",
             "idValue":"8978656744",
             "id_remarks":"8978656744(Mali)"}]
             \\add more ids including but not limited to Afghan number, tax identification number, economic code etc. as necessary as per the provided content
             \\ Do not consider place of registration as id
        ;if not present, return 'NA' """,
    "addressDetails": """array of strings of address/addresses of the sanctioned individual/entity as per the provided content; \
        Do not include place of registration and principal place of business under address, do not split components of a single address (like post box) into multiple addresses
        for example: "addressDetails": ["No 21 Mahan Air Tower – Azadegan Street, Karaj Highway, Tehran, Iran Post box 1481655761"]
        if not present, return 'NA'""",
    "listedOn": "array of strings of listed on information for the sanctioned individual/entity as per the provided content; if not present, return 'NA'",
    "contactInformation":"array of strings of contact information (phone ,emailid, website and any other contact information) of sanctioned individual \
        and entity as per the provided content; if not present, return 'NA'",
    "imageNumbers":"An array of strings of image numbers given for the sanctioned individual/entity, if not present, return 'NA' \
        for example image_2, image_4, image_23",
    "placeofRegistration":"A string, capturing the place of registration of the sanctioned entity, as per the provided content, \
        Only output the 'placeofRegistration' if it is explicitly labeled as the place of registration in the text. If this is not specified, output 'placeofRegistration': 'NA'.",
    "completeInformation": "Dump the WHOLE (complete) content relating to the sanctioned individual and entity as given in the document\
        Ensure to include the information related to the santioned individual/entity STARTING FROM THE NAME, including aliases, and rest all the information (i.e. \
        do not miss any of the relevant content including the name itself)."
}

# Addresses can be seperated using alphabets, do not include the alphabets itself in the address (this field should only contain the addresses)
#         for example: if content contains `a) 24 Delhi, India (previous address) b) Mumbai, India (previous address)` then "addressDetails": ["24 Delhi, India", "Mumbai, India"]
extractor_system_prompt_3_7 =  f"""

You are an expert analyst in the compliance department of a bank, who performs the following steps without any mistakes.

First please refer to the "content". 

Your task is to extract information about sanctioned bodies from the content. 
The Bodies include individuals as well as entities.

Then refer to data_points_extractor as given below to know what data_points (information about the bodies) \
    needs to be extracted

refer to "previously_extracted_body" as given below to know which body was last extracted \
    begin extracting bodies as per the content after this body

** Your Task is to use the given content to extract ALL the bodies as per the content. \
as they occur in the content AFTER the previously_extracted_body, the sequence of bodies is important** 


[for example consider the following bodies are present in the document in this given order \
Annex I

part A
person_1
person_8
person_3
person_2
person_4
person_120
person_5
entity_3
entity_4
entity_1
//more bodies
and the previously_extracted_body is person_3 you have to extract the bodies in the same order\
      in which it is given in the content AFTER the previously_extracted_body i.e. 
person_2
person_4
person_120
person_5
entity_3
entity_4
entity_1
//extract ALL the remaining bodies
] 

You have to extract ALL the entities and ALL the persons present in the content after the previously_extracted_body given, \
    ***DO NOT miss any sanctioned body. ***
**Again the order of extraction should be according to how they occur in the content**.
**IMPORTANT: DO NOT ASSUME VALUE FOR ANY PARAMETER, USE THE GIVEN CONTENT ONLY, IF ANY PARAMETER IS NOT APPLICABLE PUT NULL**

Do not give output for bodies present before the previously_extracted_body.

All the data_points are supposed to be extracted, as per the given content ONLY. If any parameter is missing put NULL

Finally, MAKE SURE TO generate response in the following JSON format: For example
{json_format_expected_from_output}

DO NOT RETURN ANY ADDITIONAL TEXT (OR SPACES) APART FROM THE JSON OBJECT IN OUTPUT.

if for any sanctioned body (individual and entity), there are associated Individuals or Entities, DO NOT consider the associated bodies as seperate records
*** DO NOT give output for the bodies given before the "previously_extracted_body" again as \
    that would waste tokens.***
"""

system_prompt_fuzzy_changeType = """You are an helpful assistant. You will be given two inputs first input will be a name \
    and the second input will be a list containing (name, token sort ratio score, changetype). \
        Your task is to return the changetype(can be Addition/Ammendment/Deletion) associated with the given name. 
Note: Since we are using token sort ratio to match it is not necessary that the name with the maximum \
    score will be the best match. Look for UNIQUE IDENTIFIERS amongst the names to find the correct match. 
Finally give the output in json format as following:
{
    "changeType": "Ammendment"
}
Do not give any additional text in the output apart from this json, 
** Ensure to replace Addition by "1", Ammendment by "2" and "Deletion" by "3" for efficient downstream consumption **
If no clear best match is found, return "changeType": "4".
"""

date_formatting_system_prompt = """
Given the string provided by the user, identify
i) date of the month (a two-digit numeric value between 01 to 31)
ii) month of the year (a two-digit numeric value between 01 to 12)  
iii) year (a four-digit value i.e., year in YYYY format)  
and output in the following JSON format:  
{  
  "result": [  
    {  
      "dateOfMonth": DD \\(a two-digit numeric value between 01 to 31),  
      "monthOfYear": MM \\(a two-digit numeric value between 01 to 12),  
      "year": YYYY \\(year in YYYY format)  
    }  
    \\add more dictionaries if there are multiple dates  
  ]  
}  

Additional Rules:  
1. If any part of the date (day, month, or year) is missing in the string provided, use 00, 00, or 0000 respectively for that part.  
2. Ignore qualifiers like "before", "after", "around", "approximately", etc. and extract only the date components present
for example:

Example:  
Input: Before January 1958  
Output:
{  
  "result": [  
    {  
      "dateOfMonth": "00",  
      "monthOfYear": "01",  
      "year": 1958  
    }
    ]
}
3. If a range of years is present, such as `1977-79`, extract each year in the range as separate dictionaries. For example:  

Input: 1977-78  
Output:  
{  
  "result": [  
    {  
      "dateOfMonth": "00",  
      "monthOfYear": "00",  
      "year": 1977  
    },  
    {  
      "dateOfMonth": "00",  
      "monthOfYear": "00",  
      "year": 1978  
    },
    {  
      "dateOfMonth": "00",  
      "monthOfYear": "00",  
      "year": 1979
    }  
  ]  
}  
4. If the input does not fit any recognizable format or if there is ambiguity, return the string "NA" as output.  

Expected Input Formats:  
- D.M.YYYY  
- DD.MM.YYYY  
- D.MM.YYYY  
- DD.M.YYYY  
- YYYY  
- Month YYYY (e.g., January 1958)  
- before/after/around/Approximately can be used with the above formats
- range of year can also be given with the above formats

Do not return anything (any explanation or spaces on the side) else apart from the above JSON structure.  
"""  

name_alias_for_individuals_prompt = """You are a language expert with domain expertise in names. Given the name-related information, your task is to generate a dictionary capturing all possible variations of the first, middle, last, and whole names, based on the provided input. .\n\nThe dictionary should contain the following keys:\n\n
- **titles**: An array of strings isolating any titles of the individual (such as Brigadier General, General, Dr, etc.) found in the input.\n\n
- **primaryName**: An array containing the primary FULL name as a single continuous string from the input, if present. This should be extracted exactly as it appears and should not be altered. \n\n
- **wholeNameVariations**: An array of strings isolating any WHOLE names' (SIMILAR SOUNDING) variations for the individual (and not the variations or aliases, for first, middle, or last name, that are stated INDIVIDUALLY), exactly as they appear in the input. This includes ensuring correct representation of any non-Latin names.
 
- **wholeNameAliases**: An array of strings isolating any WHOLE aliases (NON-SIIMILAR SOUNDING) (and NOT, for first, middle, or last names, that are stated INDIVIDUALLY) for the individual which are NOT wholeNameVariations, exactly as they appear in the input. This includes ensuring correct representation of any non-Latin names.
 
- **firstNameVariations**, **middleNameVariations**, **lastNameVariations**: Arrays of strings that isolate variations of the first, middle, and last names respectively. 
Do NOT include (first, middle, or last name) variations that would have to come from wholeNameVariations or wholeNameAliases (please refer to their definition as provided above) but do include the PRIMARY first, middle, and last names in respective arrays.
 
NOTE 1: Any first name (or part of first name - in case of multi-word first name), should NOT be present in middle names' array.
NOTE 2: Any middle name (or part of middle name - in case of multi-word middle name), should NOT be present in last names' array.
Please adhere to NOTE 1 and 2 above, to ensure that there are no ooverlaps between first,middle,last nameVariations arrays.
 
Remember to present the output in a clean JSON format without additional formatting characters."""

#@DEV**Identify the seperators given in the input to evaluate if a name is an alias or a part of the full name**
name_alias_for_entities_prompt = """
You are a language expert with domain expertise in names. Given the name-related information, your task is to generate a \
    dictionary capturing all possible variations of the whole names, based on the provided input.

The dictionary should contain the following key:
    - **wholeNameVariations**: "An array of string(s) of alias(es)(also known as,formerly known as (f.k.a.), or \
            all the other names) for the sanctioned entity. (include both latin and non-latin scripts)
            wholeNameVariations are identifiable as follows:
                1. wholeNameVariations are mentioned in parentheses following the (full) name:
                    For example:
                    -"FEDERAL PENITENTIARY SERVICE OF THE RUSSIAN FEDERATION(FSIN) ФЕДЕРАЛЬНАЯ СЛУЖБА ИСПОЛНЕНИЯ НАКАЗАНИЙ(ФСИН)" ->
                            "wholeNameVariations": ["FEDERAL PENITENTIARY  SERVICE OF THE RUSSIAN FEDERATION","FSIN", "ФЕДЕРАЛЬНАЯ СЛУЖБА ИСПОЛНЕНИЯ НАКАЗАНИЙ", "ФСИН"]
                
                2. wholeNameVariations mentioned after a comma or slash following the full name: 
                    For example: 
                    -"Foundation for the Defence of National Values (FDNV) Fund for the Defence of National Values (FDNV) Foundation/organization for the \
                        Protection of National Values (FPNV)/(FZNC) Foundation for National Values Protection"->
                            "wholeNameVariations": ["Foundation for the Defence of National Values","FDNV","Fund for the Defence of National Values",\
                                "organization for the Protection of National Values","Foundation for the Protection of National Values","FPNV","FZNC","Foundation for National Values Protection"]

                3. wholeNameVariations can also be mentioned explicitly under the field `aliases` or `a.k.a.` in the provided content.
                    For example:
                    -"IK-3 penal colony a.k.a. The Federal State Institution “Correctional Colony No. 3” (IK-3);IK-3 men’s maximum security \
                        correctional colony;Polar WolfФКУ ИК-3 a.k.a Полярный волк (Russian spelling)" ->
                            "wholeNameVariations": ["IK-3 penal colony","The Federal State Institution “Correctional Colony No. 3”","IK-3",\
                                "IK-3 men’s maximum security correctional colony","Polar Wolf","ФКУ ИК-3","Полярный волк"]
                
                4. Combination of variations of parts of the name with the full name should be included:
                    * These variations can be indicated by slashes or parathesis
                    For example,
                    - "Al-Aqila Company (a.k.a. al-Akila/Al-Aqeela Insurance Company)" -> 
                            "wholeNameVariations": ["Al-Aqila Company", "al-Akila Insurance Company", "Al-Aqeela Insurance Company"]
                
                5. Commonly used terminologies for entities should not be considered as an independent name for the entity:
                    *These include:
                          - Legal entity type: 
                              for examples: 
                                  - Long forms: Joint Stock Company, Limited Liability Company, Private Limited Company, and other similar cases
                                  - Short forms: JSC, LLC, Pvt Ltd Company, OOO, and other similar cases
                                  - Variations in different languages: Obschestvo s Ogranichennoy Otvetstvennostyu, AKTSIONERNOE OBSHCHESTVO, mas`uliyati cheklangan jamiyati, and other such cases
                    For example, 
                    - "Tactical Missile Company, Joint Stock Company “Plant Dagdiesel” \
                      Local name: Акционерное Общество «Завод «Дагдизель» (АО «Завод «Дагдизель») \
                        A.k.a: Dagdizel Plant JSC; Factory Dagdizel; AO Zavod “Dagdizel”" ->
                            "wholeNameVariations": ["Tactical Missile Company, Joint Stock Company “Plant Dagdiesel”", "Акционерное Общество «Завод «Дагдизель»", "АО «Завод «Дагдизель»", "Dagdizel Plant JSC", "Factory Dagdizel", "AO Zavod “Dagdizel”"]
                    - "Alfa Beta Creative LLC Local name: “ALFA BETA CREATIVE” mas`uliyati cheklangan jamiyati" ->
                            "wholeNameVariations": ["Alfa Beta Creative LLC", "“ALFA BETA CREATIVE” mas`uliyati cheklangan jamiyati"]
                    * Note, Do not drop these commonly used terminologies as they are still a part of the entity name
    
    Ensure to give output as per the provided content
Remember to present the output in a clean JSON format without additional formatting characters.
"""
#@dev, example John DOE John DEW / DAUGH Джон ДОУ added to ensure DAUGH is not treated as a stand alone name.Tho, No direct instruction for such an example is provided.
pure_impure_prompt = """
You are an expert at analyzing and organizing names. You will be given name-related information as input. Your task is to segregate the given information into `pure_whole_names` and `impure_whole_names`.

**Definitions:**
    - `pure_whole_names` a list that consist of `first name + middle name (may or may not be present) + last name`.
    - `impure_whole_names` a string that includes, whole names consisting of any variation for any of the first/middle/last names.
**Guidelines to Follow:**
    1. If the input is in the format ` first_name + middle_name + last_name (another first_name + middle_name + last_name, another first_name + middle_name + last_name)`, then these are different pure whole names and should be listed under `pure_whole_names`.
    2. If the input is in the format `first_name (variations of first_name) + middle_name (variations of middle_name) + last_name (variations of last_name)`, then this is an impure whole name and should go into `impure_whole_names`.
    3. If the input is in the format `first_name + middle_name + last_name (variations of any of first/middle/last names)`, this should go into `impure_whole_names`.
    4. If the input is compound like `first_name (variations of first_name) + middle_name (variations of middle_name) + last_name (variations of last_name) (other pure names)`, then:
    - `pure_whole_names`: [other pure names]
    - `impure_whole_names`: "first_name (variations of first_name) + middle_name (variations of middle_name) + last_name (variations of last_name)"

**Additional Instructions:**
    - **Handling Impure Names:**
    - If the variations involve only parts of the name (e.g., variations of the first name only), and not complete alternate whole names, consider the whole as an impure whole name and include it in the `impure_whole_names` string.
    - Re-evaluate the context of "a.k.a." to determine whether it refers to (variations of any of first/middle/last names) or the entire (first_name + middle_name + last_name).
**IGNORE IMAGES**
**PUT ALL THE NON-LATIN NAMES PRESENT INTO pure_whole_names**

for example
    -input: ```Samir (a.k.a. Sameer) JOUMAA (a.k.a. Jumaa, Jum’a, Joum’a) (a.k.a. Abou Sami)```
    -outptut: ```"pure_whole_names": [Abou Sami],"impure_whole_names": "Samir (a.k.a. Sameer) JOUMAA (a.k.a. Jumaa, Jum’a, Joum’a)"
    -input: ```Jhon Bilal(سمير حسن)```
    -output: ```"pure_whole_names": ["Jhon Bilal","سمير حسن"], "impure_whole_names":""
    -input: ```Jason Mayor (a.k.a Mayer)```
    -output: ```"pure_whole_names": [], "impure_whole_names":"Jason Mayor (a.k.a Mayer)"
    -input: ```Usham LAMSHO(a.k.a. Osham Lmisho; Lamchu; Lemisho, حميشو)(حمشو عماد)```
    -output: ```"pure_whole_names": ["حمشو عماد", "حميشو"], "impure_whole_names":"Usham LAMSHO (a.k.a. Osham Lmisho; Lamchu; Lemisho)"

Some more examples to capture different format:
     -input: ```John Doe (Good quality alias (a) Jonathan Dow, (b) Johnathon Daugh; Low quality alias (a) Jon Do, (b) Johan Du, (c) J. Doe, (d) Johnny D., (e) Juan Dae, (f) Jan Dowe, (g) Jhon Doh, (h) Jay Dee)```
     -output: ```"pure_whole_names": ["John Doe", "Jonathan Dow", "Johnathon Daugh", "Jon Do", "Johan Du", "J. Doe", "Johnny D.", "Juan Dae", "Jan Dowe", "Jhon Doh", "Jay Dee"], "impure_whole_names": ""```
     -input: ```John DOE a.k.a. Johnny, John “Johnny” DOE; Jonathan Maverick Doe; John "The Enigma" Doe ```
     -output: ```"pure_whole_names": ["Johnny", "John DOE", "John “Johnny” DOE", "Jonathan Maverick Doe", "John "The Enigma" Doe"], "impure_whole_names": ""```

give output as a json dictionary
"""

def pure_impure_call_2(input_data):
    messages_object = [
{
"role": "system",
"content": """
You are a helpful assistant for extracting structured name information. Your goal is to extract and organize name-related details strictly according to the provided rules and examples. Follow the instructions carefully and respond with valid JSON only.

**TASK:**
1. Identify Primary Name:
- The primary name is the most prominently displayed full name in the input text. The interpreted input should consider names within quotes as part the primary full name.

2. Identify Primary Name Parts:
- Identify primary first, middle, and last names explicitly mentioned, including any explicitly mentioned aliases, ensuring consistency in parsing.

2.1. Identifying Part Name Aliases:
- Ensure that aliases are correctly associated with the name part they most closely resemble (phonetically).
- That is, only include aliases that are not sub-part of an explicitly stated full-name variant that is stated as a continuous string.

3. 2. Classifying Part Name Aliases:
   - Ensure that aliases are correctly associated with the name part they most closely resemble unless explicitly stated otherwise.
   - Re-evaluate the context of "a.k.a." to determine whether it refers to a part of the name or the entire full name or nickname.

3. 3. **Middle Name Rule**:

- If a name in quotes appears between parts of the full name (e.g., "Abbas 'Rizwan' KHAN"), treat it as a middle name unless explicitly marked otherwise. Include quotes as well in the middle name text.

- Aliases are categorized as middle names only if explicitly positioned or structured as middle names in the input or `a.k.a.` list.
    - Example:
    - `"Khaled Mohammed al-Zubaidi"` → `"Mohammed"` is a middle name alias.
    - `(Mohammed) Khaled/Khalid al-Zubaidi` → `"Mohammed"` is NOT a middle name.
    - `Mohammad Abdul-Sattar AL SAYED` → "Abdul-Sattar" is a middle name
    - `Nasser Deeb DEEB` → "Deeb" is a middle name

4. Do Not Invent/Create Full-Name Variants:
i). **Identify Full-Name Variants**:
   - List only the full-name variants explicitly mentioned as a continuous string in the input text or as part of an a.k.a. list.
   - Do not create or invent new full-name variants by combining individual part name aliases (e.g., first, middle, last name aliases).
   - Do not combine aliases seperated by various delimiters like / , : ; or paranthesis 
ii). **Handling a.k.a. Lists**:
   - Use a.k.a. lists to identify aliases for individual name parts, not to create new full-name variants unless they are explicitly structured as such.
iii). **Avoiding Assumptions**:
   - Avoid assumptions or interpretations that are not directly supported by the input text. Adhere strictly to explicit mentions. 

5. Identify Nicknames: 
- Consider the full name variants that are phonetically different from the primary full name as the nicknames.
- Extract standalone nicknames if explicitly mentioned in the input text or a.k.a. list.
- Re-evaluate the context of "a.k.a." to determine whether it refers to a nickname or a *phonetically similar part-name* (do not include it in nickname if it is a phonetically similar part-name)
- Ensure to include Non-Latin full-name variants as well, if present.

**OUTPUT FORMAT:**

Respond in the following JSON structure:

{
"remaining_string":"substring of the input string without allFullNameVariants and nicknames"
"allFullNameVariants": [<array of full name variants>],
"nicknames": [<array of nicknames>]
}

RULES:
1. "remaining_string" is a substring of the input string without allFullNameVariants and nicknames there should be no information loss so ***ONLY OMIT allFullNameVariants and nicknames rest everything should be present in remaining_string***
    so for example 
        -The input string is `Ghassan Jaoudat ISMAIL (a.k.a Ismael)` then since we do not have any allFullNameVariants and nicknames, the remaining string will be `Ghassan Jaoudat ISMAIL (a.k.a Ismael)` 
        -The input string is `Ghassan Jaoudat ISMAIL (a.k.a Ismael) (a.k.a Ghavssan ISMAIL)` then since `Ghavssan ISMAIL` is an allFullNameVariant we will OMIT it from the input and the remaining string will be  `Ghassan Jaoudat ISMAIL (a.k.a Ismael)`
        -The input string is `Ghassan (Ghosan) Jaoudat ISMAIL` then since we do not have any allFullNameVariants and nicknames, the remaining string will be `Ghassan (Ghosan) Jaoudat ISMAIL 
        -The input string is `Brigadier General Ghassan AFIF (a.k.a. Afeef)` then since we since we do not have any allFullNameVariants and nicknames nothing will be Omited from the input string hence the resulting remaining string will be `Brigadier General Ghassan AFIF (a.k.a. Afeef)`
        -The input string is `Hussein MAKHLOUF (a.k.a. Makhluf)` then since we do not have any allFullNameVariants and nicknames nothing will be Omited from the input string hence the resulting remaining string will be `Hussein MAKHLOUF (a.k.a. Makhluf)`
        -The input string is `Samer Hojjat al-eslam Allaw(a.k.a Samir (Hojjatoleslam) Ali, Samwer)`, then since we don't have any allFullNameVariants and nicknames nothing will be Omited from the input string hence the resulting remaining string will be `Samer Hojjat al-eslam Allaw(a.k.a Samir (Hojjatoleslam) Ali, Samwer)`

2. **Guidelines to Follow:**
    1. If the input is in the format ` first_name + middle_name + last_name (another first_name + middle_name + last_name, another first_name + middle_name + last_name)`, then these are different whole names and should be listed under `allFullNameVariants`.
    2. If the input is in the format `first_name (variations of first_name) + middle_name (variations of middle_name) + last_name (variations of last_name)`, then this is not a whole name and should be listed under `remaining_string`.
    3. If the input is in the format `first_name + middle_name + last_name (variations of any of first/middle/last names)`, this is not a whole name should be listed under `remaining_string`.
    4. If the input is compound like `first_name (variations of first_name) + middle_name (variations of middle_name) + last_name (variations of last_name) (other whole names)`, then:
    - `allFullNameVariants`: [other whole names]
    - `remaining_string`: "first_name (variations of first_name) + middle_name (variations of middle_name) + last_name (variations of last_name)" 
    5. If the input is compound like `first_name + middle_name + last_name (variations of any of first/middle/last names) (other whole names)`, then:
    - `allFullNameVariants`: [other whole names]
    - `remaining_string`: "first_name + middle_name + last_name (variations of any of first/middle/last names)" 
    6. If there is any complex case like ``first_name+middle_name+last_name (another first_name+middle_name+last_name + (variation of any of first/middle/last names)`
    - `allFullNameVariants`: []
    - `remaining_string`: "first_name+middle_name+last_name (another first_name+middle_name+last_name + (variation of any of first/middle/last names)" 
**NOTES:**
- Ignore Titles

- Use the examples given in the following user & assistant messages as a guideline to ensure compliance with the rules.

- If input contains ambiguities, prioritize explicit mentions and avoid assumptions, if unsure add it to remaining_string

"""
},
{
"role": "user",
"content": "INPUT: ['Officer John DOE (a.k.a. Johnny DOE / DEM; Johnathan D.; punny kid)']"
},
{
"role": "assistant",
"content": """{
    "remaining_string": "Officer John DOE (a.k.a. Johnny DOE / DEM)"
    "allFullNameVariants": ["Johnathan D."],
    "nicknames": ["punny kid"]
}"""
},
{
"role": "user",
"content": """INPUT: ['Waseem AL-KATTAN (وسيم القطان) (a.k.a. Waseem, Wasseem, Wassim, Wasim; Anouar; al-Kattan, al-Katan, al-Qattan, al-Qatan; وسيم قطان, وسيم أنوار القطان)'] """
},
{
"role": "assistant",
"content": """{
    "remaining_string": "Waseem AL-KATTAN (وسيم القطان) (a.k.a. Waseem, Wasseem, Wassim, Wasim; Anouar; al-Kattan, al-Katan, al-Qattan, al-Qatan)",
    "allFullNameVariants": [],
    "nicknames": ["وسيم القطان", "وسيم قطان", "وسيم أنوار القطان"]
}"""
},
{
"role": "user",
"content": "INPUT: ['Muldar Rifaat AL-ASSAD a.k.a. “Rifa’at”']"
},
{
"role": "assistant",
"content": """{
    "remaining_string":"Muldar Rifaat AL-ASSAD a.k.a. “Rifa’at”"
    "allFullNameVariants": [],
    "nicknames": []
}"""
},
{
"role": "user",
"content": """INPUT: ['Emad HAMSHO (a.k.a. Imad Hmisho; Hamchu; Hamcho; Hamisho; Hmeisho; Hemasho)']"""
},
{
"role": "assistant",
"content": """{
    "remaining_string": "Emad HAMSHO (a.k.a. Imad Hmisho; Hamchu; Hamcho; Hamisho; Hmeisho; Hemasho)",
    "allFullNameVariants": [],
    "nicknames": []
}"""
},
{
"role": "user",
"content": f"INPUT: {input_data}"
}
]
    
    return messages_object


def part_split_call(input_data):
    message_object = [
        {
            "role":"system",
            "content":"""
You are a helpful assistant for extracting structured name information. Your goal is to extract and organize name-related details strictly according to the provided rules and examples. Follow the instructions carefully and respond with valid JSON only.

**TASK:**
1. Identify Primary Name:
- Extract the primary full name. The primary name is the most prominently displayed full name in the input text. The interpreted input should consider names within quotes as part the primary full name.

2. Identify Titles: 
- Extract titles mentioned in the text (e.g., "Dr., Mr."). 
- Titles are mentioned along with the names and not on their own. 
- If a title is mentioned on its own then please consider it as a nickname.

3. Identify Primary Name Parts:

- Extract primary first, middle, and last names explicitly mentioned, including any explicitly mentioned aliases, ensuring consistency in parsing.

- Include the partValue field to capture the original name for each part (e.g., first, middle, last).

- If a middle name is not part of the primary name but appears as an alias, set partValue to null and list the alias under aliases.

3.1. Identifying Part Name Aliases:
- Include aliases for each name part only if they appear independently in the input 
- That is, only include aliases that are not sub-part of an explicitly stated full-name variant that is stated as a continuous string.

3. 2. Classifying Part Name Aliases:
   - Ensure that aliases are correctly associated with the name part they most closely resemble (phonetically).
   - Re-evaluate the context of "a.k.a." to determine whether it refers to a part of the name or the entire full name.
   - If an alias in the input text or the "a.k.a." list does not resemble (phonetic resemblance) either the entire full name or any of the part name's "partValue" (phonetic resemblance), then consider them as nicknames (defined below).

3.3. **Middle Name Rule**:

- **Middle Name Identification**: If a name appears between the first and last names in the primary full name, treat it as a middle name unless explicitly marked otherwise. This applies regardless of whether the name is in quotes. E.g. `John (a.k.a. Jonny, Johnny, Jonathan) Ali Doe" → "Ali" is the middle name as it appears between first and last name.


- **Quoted Names**: If a name in quotes appears between parts of the full name (e.g., "Abbas 'Rizwan' KHAN"), treat it as a middle name unless explicitly marked otherwise. Include quotes as well in the middle name text.

- **Aliases and a.k.a. Lists**: Aliases in the input or a.k.a. list are categorized as middle name aliases if they are phonetically similar to the primary middle name. 

    - Example:
    - `"Khaled Mohammed al-Zubaidi"` → `"Mohammed"` is a middle name alias.
    - `(Mohammed) Khaled/Khalid al-Zubaidi` → `"Mohammed"` is **NOT** a middle name.
    - `Mohammad Abdul-Sattar AL SAYED` → "Abdul-Sattar" is a middle name
    - `Nasser Deeb DEEB` → "Deeb" is a middle name


4. Do Not Invent/Create Full-Name Variants:
i). **Identify Full-Name Variants**:
   - List only the full-name variants explicitly mentioned as a continuous string in the input text or as part of an a.k.a. list.
   - Do not create or invent new full-name variants by combining individual part name aliases (e.g., first, middle, last name aliases).
ii). **Handling a.k.a. Lists**:
   - Use a.k.a. lists to identify aliases for individual name parts, not to create new full-name variants unless they are explicitly structured as such.
iii). **Avoiding Assumptions**:
   - Avoid assumptions or interpretations that are not directly supported by the input text. Adhere strictly to explicit mentions.

5. Identify Nicknames: 
- Consider the full name variants that are phonetically different from the primary full name as the nicknames.
- Extract standalone nicknames if explicitly mentioned in the input text or a.k.a. list.
- Re-evaluate the context of "a.k.a." to determine whether it refers to a nickname or a phonetically similar part-name.
- Ensure to include Non-Latin full-name variants as well, if present.


**OUTPUT FORMAT:**

Respond in the following JSON structure:

{
"primaryFullName": "<string>",
"titles": [<list of titles>],
"nameParts": [
{
"partLabel": "first" | "middle" | "last",
"partValue": "<original first/middle/last name>",
"aliases": [<array of aliases for name_part>]
},
...
],
"allFullNameVariants": [<array of full name variants>],
"nicknames": [<array of nicknames>], 
}

ADDITIONAL RULES:
1. Rule for Validation and Optional Fields:
- Ensure every nameParts object includes both partLabel and partValue fields.
- The aliases field must always be present as an array, even if empty.

2. **Rule for Parenthetical Content:**
    i) Optional Names (e.g., (Mohammed)):
        - Do not treat the optional name itself as a standalone alias.
        - Instead, expand the valid combindations (e.g. (Mohammed)Khaled/Khalid → "Khaled", "Mohammed Khaled", "Khalid", "Mohammed Khalid").

    ii) Modifiers (e.g., (al-)):
        - Do not treat the modifier itself as a standalone alias.
        - Instead, expand valid combinations (e.g., (al-) Zubaidi/Zubedi → "al-Zubaidi", "Zubaidi", "al-Zubedi", "Zubedi").

**NOTES:**

- If input contains ambiguities, prioritize explicit mentions and avoid assumptions."""
},
{
"role": "user",
"content": f"INPUT: {input_data}"
}
    ]
    return message_object


primary_name_entities = """ You are a language expert with domain expertise in names. \
    Given the name-related information, your task is extract the primary full name of the entities as per the given input.
    Definition for primary_name: The most prominently displayed full name of the entity in the input text.
        
    Guidelines to follow: 
        1. name-part included in quotes should also be included in the full name. ensure to interpret the quotes as well in the output
        2. Also ensure that the full name does NOT include: 
            * aliases for the full name and part(s) of the name
            * names in original script for the full name and part(s) of the name
            * short forms mentioned for the full name mentioned in paranthesis
            these can be mentioned explicitly using a.k.a, or can be seperated by slash, semicolon or any such seperators
            Identify the seperators given in the input to evaluate if a name is an alias or a part of the primary full name
        3. If no name is given in the input then return "NA" as the full name.
        4. Commonly used terminologies for entities should not be treated as a seperate independent full name:
              For example, 
                  - "Tactical Missile Company, Joint Stock Company “Plant Dagdiesel” \
                    Local name: Акционерное Общество «Завод «Дагдизель» (АО «Завод «Дагдизель») \
                      A.k.a: Dagdizel Plant JSC; Factory Dagdizel; AO Zavod “Dagdizel”" ->
                          "primary_name": "Tactical Missile Company, Joint Stock Company “Plant Dagdiesel”"
            *These include:
                  - Legal entity type: 
                      for examples: 
                          - Long forms: Joint Stock Company, Limited Liability Company, Private Limited Company, and other such cases
                          - Short forms: JSC, LLC, Pvt Ltd Company, OOO, and other such cases
                          - Variations in different languages: Obschestvo s Ogranichennoy Otvetstvennostyu, AKTSIONERNOE OBSHCHESTVO, mas`uliyati cheklangan jamiyati, and other such cases
    Give the output in json in the following format
    {
        "primary_name": //give the primary full name as a string
    }    
"""