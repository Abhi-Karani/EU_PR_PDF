from typing import Union
from config.config import Config
import utils.eu_utils.eu_common_utils as eu_common_utils
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import PromptTemplate, ChatPromptTemplate
from langchain_openai import ChatOpenAI
from langchain.output_parsers import PydanticOutputParser
from langchain_community.callbacks.manager import get_openai_callback

from openai import OpenAI

from pydantic import BaseModel, Field, ConfigDict
from typing import List, Dict, Optional, Union

class IdDetail(BaseModel):
    idType: str = Field(description="type of the concerned id as given in the content \
        for example: 'Registration number', 'Passport number'")
    idValue: str = Field(description="The alpha-numeric code of the concerned id as given in the content\
        for example: '123456789', '8978656744'")
    id_remarks: str = Field(description="any other information about the concerned id as per the given content\
        for example: 'BVL', '8978656744(Mali)'")
    
class CountryName(BaseModel):
    countryName: str = Field(
        description="name of the Country for example Australia instead of Australian"
    )

class Record(BaseModel):
    entityType: str = Field(
        description="Individual, Entity or Vessel; determined based on heading/description accompanying \
            the details of the record or the list of records or the table of records, as per the provided content"
    )
    name: str = Field(
        description="""Full name of the sanctioned individual/entity as per the given content.
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
            7. "Anant Kiran Gupta (Goopta)" -> Name: "Anant Kiran Gupta
            
            Furthermore, if no name for an individual/entity is given then return "ALL" as the full name."""
    )
    name_info: str = Field(
        description="""The complete information about *only* the name (latin script names and non latin script names) of an individual \
        and an entity *exactly as given in the document*, including any "names", "aliases", "a.k.a", "formerly known as",\
            "also known as" ,"orginal script names", "original script aliases", "maiden names", "names in all the languages" etc. 
            as per the given content, *Ensure accuracy and do not infer or add any information beyond the provided content*"""
    )
    designation: Union[List[str], str] = Field(
        default="NA",
        description="Designations held by the sanctioned individual/entity, as per the provided document"
    )
    placeOfBirth: Union[List[str], str] = Field(
        default="NA",
        description="Place(s) of birth of the sanctioned individual, as per the provided document"
    )
    dateOfBirth: Union[List[str], str] = Field(
        default="NA", 
        description="Date(s) of birth of the sanctioned individual, as per the provided document"
    )
    nationality_Country_Name: Union[List[CountryName], str] = Field(
        default="NA",
        description="""names of all the Countries where the sanctioned individual has a nationality, \
            as mentioned explicitly in the given content, by phrases such as \
                'national of [Country(s)]' or '[Country(s)] national' or 'nationality [Country(s)]' 
        Do not infer nationality from birth, citizenship or any other identifiers"""
    )
    citizenship_Country_Name: Union[List[CountryName], str] = Field(
        default="NA",
        description="""names of all the Countries where the sanctioned individual holds citizenship \
            as mentioned explicitly in the given content. by phrases such as \
            "citizen of [Country(s)]" or "[Country(s)] citizen" or "citizenship [Country(s)]" 
        Do not infer citizenship from birth, nationality or any other identifiers.""",
    )
    gender: str = Field(
        default="NA",
        description="Gender of the sanctioned individual, as per the provided document"
    )
    idDetails: Union[List[IdDetail], str] = Field(
        default="NA",
        description="List of all the ids for an individual/entity, as per the provided document\
            add all the ids including but not limited to Afghan number, tax identification number, economic code etc.\
                Do not consider place of registration as id"
    )
    addressDetails: Union[List[str], str] = Field(
        default="NA",
        description="""All the address/addresses of the sanctioned individual/entity as per the provided content; \
            Do not include place of registration and principal place of business under address, do not split components of a single address (like post box) into multiple addresses\
                for example: ["No 21 Mahan Air Tower – Azadegan Street, Karaj Highway, Tehran, Iran Post box 1481655761"]"""
    )
    listedOn: Union[List[str], str] = Field(
        default="NA",
        description="Listed on information for the sanctioned individual/entity, as per the provided document"
    )
    contactInformation: Union[List[str], str] = Field(
        default="NA",
        description="Contact information (phone ,emailid, website and any other contact information), as per the provided document"
    )
    placeofRegistration: str = Field(
        default="NA",
        description="Place of registration of the sanctioned entity, as mentioned explicitly in the provided document"
    )
    completeInformation: str = Field(
        description="the WHOLE (complete) content relating to the sanctioned individual and entity as given in the document\
        Ensure to include the information related to the santioned individual/entity STARTING FROM THE NAME, including aliases, and rest all the information (i.e. \
        do not miss any of the relevant content including the name itself)."
    )

class Result(BaseModel):
    result: List[Record] = Field(
        description="all of the sanctioned individuals and entities as per the provided content",
        default=[]
    )
    
parser = JsonOutputParser(pydantic_object=Result)
output_format_records = parser.get_format_instructions()
    
input_con = [
                ": ‘46.",
                "Name: Mohammad ESLAMI\n(ﻣﺤﻤﺪﺍﺳﻼﻣﯽ)",
                "Identifying information: DOB: 23.9.1956\nPOB: Isfahan, Iran\nFunction: Head of theAtomic Energy\nOrganization of Iran; Vice President\nof Iran\nRank: Brig. General\nNationality: Iranian\nGender: male\nPassport no.: D10008684\n(Diplomatic Passport)",
                "Reasons: As Head of the Atomic Energy Organization of Iran and Vice President of Iran,\nIRGC Brig. General Mohammad Eslami is directly associated with, or providing\nsupport for, Iran’s proliferation-sensitive nuclear activities.",
                "Date of listing: 17.10.2023\n(UN: 3.3.2008)"
            ]

open_ai_llm = ChatOpenAI(
    model=eu_common_utils.llm_for_name_alias,
    temperature = eu_common_utils.temperature,
    max_tokens = eu_common_utils.max_tokens,
    max_retries_constant_delay = eu_common_utils.max_retries_constant_delay,
    retry_delay_constant_delay = eu_common_utils.retry_delay_constant_delay,
)




def execute_lang_chain(system_prompt, format_instructions, input_content, model=llm):

    # Create prompt with system message and formatting instructions
    prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "{system_prompt}\n{format_instructions}",
        ),
            ("human", "{query}"),
        ]
    ).partial(format_instructions=format_instructions)
    # Define your chain
    chain = prompt | model | parser

    # Run the chain
    with get_openai_callback() as cb:
        response = chain.invoke({
            "system_prompt":system_prompt,
            "query": input_content
        },
    )
    return response, cb


# a = execute_lang_chain(extractor_system_prompt, parser.get_format_instructions(), input_con, model=llm)