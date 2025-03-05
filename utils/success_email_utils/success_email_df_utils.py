import pandas as pd

def convert_entities_to_df(data):
    records = []
    
    for i in range(len(data)):
        record = {}
        
        # Basic fields
        record["_id"] = data[i].get("_id")
        record["Entity Type"] = data[i].get("entityTypeName")
        if int(data[i].get("sourceActionId")) == 1:
            record["Action Type"] = "Addition"
        elif int(data[i].get("sourceActionId")) == 2:
            record["Action Type"] = "Amendment"
        elif int(data[i].get("sourceActionId")) == 3:
            record["Action Type"] = "Deletion"
        else:
            record["Action Type"] = "Error"

        # if data[i].get("primaryName") == "ALL":
        #     record["Action Type"] = "Deletion"
        
        titles = data[i].get("titles",[])
        if titles:
            record["Titles"] = "; ".join(titles)

        contacts = data[i].get("contactList",[])
        if contacts:
            record["Contact Details"] = ";".join(contacts)

        # Handle name details
        
        alias_details = []
        og_details = []
        for name_details in data[i].get("nameDetailsList", []):
            if name_details.get("nameType") == "Primary Name":
                record["Primary Name"] = name_details.get("fullName")
                record["First Name"] = name_details.get("firstName")
                record["Last Name"] = name_details.get("lastName")
            if name_details.get("nameType") == "Aliases":
                alias_details.append(name_details.get("fullName", ""))
            if name_details.get("nameType") == "Original Script Name":
                og_details.append(name_details.get("fullName", ""))
        if alias_details:
            record["Aliases"] = "; ".join(alias_details)
        if og_details:
            record["Original Script Name"] = "; ".join(og_details)

        # Handle address details
        #TODO: this requires change - i) primary and alternate addresses, ii) country field
        address_details = []
        for address in data[i].get("addressDetailsList", []):
            address_details.append(address.get("addressLine1", ""))
        
        if address_details:
            record["Address"] = "; ".join(address_details)

        # Handle ID details
        #TODO: this requires change too - i) identical idTypes are getting overwritten, ii) ability to read vectors is missing
        for id_detail in data[i].get("idNumberTypesList", []):
            id_type = id_detail.get("idType", "")
            record[id_type] = id_detail.get("idValue", "")
            record[f"{id_type} (Remarks)"] = id_detail.get("remarks", "")

        # Handle birth date details
        birth_dates = []
        for birthdate in data[i].get("birthDateDetailsList", []):
            birth_dates.append(birthdate.get("date", ""))
        
        if birth_dates:
            record["Birth Date"] = "; ".join(birth_dates)   # joining with ; to keep it consistent across various fields

        # Handle birth place details
        birth_places = []
        for birthplace in data[i].get("birthPlaceDetailsList", []):
            birth_places.append(birthplace.get("place", ""))
        
        if birth_places:
            record["Birth Place"] = "; ".join(birth_places)

        # Handle nationality details
        nationalities = []
        for nationality in data[i].get("nationalityDetailsList", []):
            nationalities.append(nationality.get("countryName", ""))
        
        if nationalities:
            record["Nationality"] = "; ".join(nationalities)    # joining with ; to keep it consistent across various fields

        # Handle citizenship details
        citizenships = []
        for citizenship in data[i].get("citizenshipDetailsList", []):
            citizenships.append(citizenship.get("countryName", ""))
        
        if citizenships:
            record["Citizenship"] = "; ".join(citizenships) # joining with ; to keep it consistent across various fields

        additional_info = data[i].get("additionalInformation")
        if additional_info:
            record["Additional Information"] = str(additional_info).strip("[]'")

        gender = data[i].get("gender")
        if gender:
            record["Gender"] = str(gender)
        
        #TODO: should you not remove the following 3 lines as they were duplicated?
        gender = data[i].get("gender")
        if gender:
            record["Gender"] = str(gender)
        
        regulations_list = data[i].get("regulationsList")
        if regulations_list:
            record["URL"] = regulations_list[0].get("publicationUrl")

        
        if "listingDateTime" in data[i]:
            record["Listing Date and time"] = str(data[i]["listingDateTime"]).strip("[]'")

        #TODO: Do we intend to include imageInfo in the excel sheet?
        #TODO: By that logic, does additional_info have base64 links of images?
        imageInfo = data[i].get("imageInfo",[])
        if imageInfo:
            record["imageInfo"] = "; ".join(imageInfo)
        
        # Append the record to the list of records
        records.append(record)
    
    # Convert the list of records into a DataFrame
    df = pd.DataFrame(records)

    desired_columns_order = [
    "_id", "Entity Type", "Action Type", "Primary Name", "First Name", "Last Name","Gender","Original Script Name", "Aliases", 
    "Titles", "Birth Date", "Birth Place", "Contact Details", "Address", 
    "Nationality", "Citizenship","imageInfo"
    ]
    columns_order = []
    for column in desired_columns_order:
        if column in df.columns:
            columns_order.append(column)


    # Add any dynamically added ID columns and their remarks
    id_columns = [col for col in df.columns if col not in columns_order + ["Additional Information", "URL", "Listing Date and time"]]
    columns_order.extend(id_columns)

    desired_columns_order_2 = ["Additional Information", "Listing Date and time", "URL"]
    for column in desired_columns_order_2:
        if column in df.columns:
            columns_order.append(column)
    # Reorder the DataFrame columns
    df = df[columns_order]
    return df