import pandas as pd
from datetime import datetime
import json
from tkinter import *
from tkinter.ttk import *

pd.set_option("display.max_colwidth", 10000) # ! Important !

SETTING_OPTIONS = {
    "Case Status": [
        "Confirmed",
        "Confirmed-Non Resident",
        "Non-Michigan Case",
        "Not a Case",
        "Probable",
        "Suspect",
        "Unknown",
    ],
    "Investigation Status": [
        "Active",
        "Canceled",
        "Completed",
        "Completed - Follow Up",
        "New",
        "Review",
        "Superceded",
    ],
}

def find_settings(df, categories = ['Case Status','Investigation Status']):
    """ 
    Takes the raw, unprocessed dataframe and extracts values for each setting in categories
    Returns dataframe settings in dictionary format {category:[options]}
    
    """
    settings = {}
    for setting in categories:
        settings[setting] = sorted([
            b.strip() for b in 
                df.iloc[df.index < 10,0].loc[                           #selecting first 10 rows, first column
                df.iloc[df.index < 10,0].str.contains(setting)==True    #selecting cell containing setting category as substring
                ].to_string().split(':')[1:][0].split(',')              #string methods to seperate values 
            ])
    return settings


def get_past_measures_diseases(list):
    """takes a list of disease names (df.columns) and returns all which follow the
    "name (Pre-year)" format
    """
    output = []
    for i in list:
        if "-2" in i:
            output.append(i)
    return output


def yeet_old_measures_diseases(list, y=5):
    """
    takes a list of measurement-year inclusive disease names
    and returns a list with only those from the past 'y' years
    """
    current_year = datetime.now().year
    keepsies = []
    while y > 0:
        for disease in list:
            if str(current_year - y) in disease:
                keepsies.append(disease)
        y -= 1
    return keepsies


def yeet_year_from_name(list):
    """
    takes a list of measurement-year inclusive names
    and returns a list of names with the year stripped
    """
    corrected = []
    for name in list:
        corrected.append(name[: (name.rfind("-2") - 5)])
    return corrected


def to_bool(str):
    """
    takes a user-input y/n string and converts to boolean T/F
    """
    if str in ["T", "t", "Y", "y"]:
        return True
    elif str in ["F", "f", "N", "n"]:
        return False
    else:
        return "Not a boolean. Try again."

def to_raw(string):
    return fr"{string}"


def df_cleaning_preprocessing(df):
    """
    Intakes raw MDSS-generated csv
    Cleans, preprocesses, and shapes data
    Returns cleaned dataframe
    """

    df = df.iloc[9:,:]
    df.columns = df.iloc[0,:]
    df = df.iloc[1:,:].set_index('Disease')
    df.reset_index(inplace=True)
    for a in ['Total','Subtotal']:
        df = df.drop(df[df['Disease']==a].index)
    df = df.drop(columns='Total')
    df = df.drop(df[df['Jan-2019'] == 'Jan-2019'].index)
    df = df.set_index(['Disease','Disease Group']).apply(pd.to_numeric, errors='ignore')
    df = df.reset_index().set_index('Disease')
    df = df.T
    past_measures = get_past_measures_diseases(df.columns)
    current_past_measures = yeet_old_measures_diseases(past_measures)
    df.drop(columns = [m for m in past_measures if m not in current_past_measures], inplace=True)
    rename_dict = {}
    for m in current_past_measures:
        rename_dict[m] = m[:(m.rfind('-2')-5)]
    df = df.rename(columns=rename_dict)
    d = {}
    for col in df.columns:
        d[col] = col.strip()
    df = df.rename(columns=d)
    df = df.rename(columns={'Shiga toxin-producing Escherichia coli --(STE':'Shiga toxin-producing Escherichia coli (STEC)', 'Shiga toxin-producing Escherichia coli --(STEC)':'Shiga toxin-producing Escherichia coli (STEC)'})
    df['Influenza-Like Illness'] = df['Flu Like Disease*'] + df['Influenza'] + df['Influenza, 2009 Novel*'] + df['Influenza, Novel']
    
    for disease in df.columns[df.columns.duplicated()]:
        df[disease+'_'] = df[disease].iloc[:,1] + df[disease].iloc[:,0]
        df[disease+'_'][0] = df[disease].iloc[0,1]
    df = df.drop(columns= [d for d in df.columns[df.columns.duplicated()]])
    b = {}
    for col in df.columns:
        b[col] = col.strip('_')
    df = df.rename(columns=b).T.reset_index()
    df = df.set_index(['Disease','Disease Group']).T.reset_index()
    df.iloc[:,0] = pd.to_datetime(df.iloc[:,0], format='%b-%Y')
    df = df.loc[df.iloc[:,0] < datetime.today(),:].T
    df.columns = df.iloc[0,:]
    df = df.iloc[1:,:]
    df = df.reset_index().set_index('Disease').T
    return df


def transpose_add_YTD(df):
    df = df.rename_axis('Disease').reset_index().T
    df.columns = df.iloc[0,:]

    df = pd.melt(df.T.drop(columns='Disease').T.reset_index().rename(columns={'index':'Disease'}), id_vars=['Disease','Disease Group'], var_name="Time", value_name='Count')
    df['Time'] = pd.to_datetime(df['Time'])
    df['Month'] = df['Time'].apply(lambda x: x.month_name())
    df['Year'] = df['Time'].apply(lambda x: x.year)
    df['Count'] = pd.to_numeric(df['Count'])
    df['YTD'] = df.groupby(['Disease','Year'])['Count'].cumsum()
    return df



class MDSS_DiseaseGroup:
    """
    A class is a type of object in python. 
    This class holds information about groups of diseases that share MDSS report-generation settings
    """

    def __init__(self,diseases=[],case_settings=[],investigation_settings=[],options=SETTING_OPTIONS):
        self.diseases = list(set(diseases))
        self.case_settings = case_settings
        self.investigation_settings = investigation_settings
        self.options = options
        self.name = ""

    def __str__(self):
        d = self.diseases
        c = self.case_settings
        i = self.investigation_settings
        return "DISEASES: " + json.dumps(d, indent=4) + '\n' + "CASE STATUS: " + json.dumps(c, indent=4) + '\n'+  "INVESTIGATION STATUS: " + json.dumps(i, indent=4)
    
    def get_settings(self):
        """
        Runs user-prompting setting functions if settings not already defined
        """
        if len(self.case_settings) == 0:
            self.define_case_settings()
        if len(self.investigation_settings) == 0:
            self.define_investigation_settings()
        self.settings = {
            'Case Status': self.case_settings,
            'Investigation Status': self.investigation_settings
        }
        return self.settings

    def define_case_settings(self):
        """
        Sets case_settings as list of user-prompted true case status settings
        """
        self.case_settings_dict = {}
        for setting in self.options["Case Status"]:
            self.case_settings_dict[setting] = to_bool(input(setting + "? (y/n): "))
        self.case_settings = sorted([a for a in self.case_settings_dict.keys() if self.case_settings_dict[a]])

    def define_investigation_settings(self):
        """
        Sets investigation_settings as list of user-prompted true investigation status settings
        """
        self.investigation_settings_dict = {}
        for setting in self.options["Investigation Status"]:
            self.investigation_settings_dict[setting] = to_bool(input(setting + "? (y/n): "))
        self.investigation_settings = sorted([a for a in self.investigation_settings_dict.keys() if self.investigation_settings_dict[a]])
        

    def add_disease(self):
        """
        Appends user-inputted diseases to list of diseases and strips duplicates
        """
        self.another_disease = True
        while self.another_disease is True:
            self.diseases.append(input("Which disease?: "))
            self.another_disease = to_bool(input("Add another? (y/n): "))
        self.diseases = list(set(self.diseases))
        print("Disease(s) added.")

    def remove_disease(self):
        """
        Removes user-inputted diseases from list of diseases and strips duplicates
        """
        self.another_disease = True
        while self.another_disease is True:
            self.diseases.remove(input("Which disease?:"))
            self.another_disease = to_bool(input("Remove another? (y/n): "))
        self.diseases = list(set(self.diseases))
        print("Disease(s) removed. ")

    def get_data(self):
        self.dataset = df_cleaning_preprocessing(pd.read_csv(input('Paste filename: ')))[self.diseases]


def prompt_user_for_path(M_DGroup):
    """
    Intakes an MDSS_DiseaseGroup instance 
    Directs user to request the correct MDSS report based on Disease Group settings
    Requests filepath for MDSS report
    Cleans and preprocesses data from MDSS report
    Appends data to output file
    """
    print("For the disease group with the following settings: ")
    print('')
    print(M_DGroup)
    print('')
    print('Do the following steps in MDSS: ')
    print('')
    print("A: Log into MDSS")
    print("B: Click on the 'Reports' tab at the top of the page")
    print("C: Click on '4. Diseases - 5 Year History'")
    print("D: Leave both boxes unckecked in 'Aggregate/Individual Cases'")
    print("E: Check 'Onset Date' in 'Time Period Based On'") 
    print("F: Use ctrl-click to select the following 'Case Status' options: ")
    print('')
    print(M_DGroup.case_settings)
    print('')
    print("G: Use ctrl-click to select the following 'Investigation Status' options: ")
    print('')
    print(M_DGroup.investigation_settings)
    print('')
    print("H: In 'Display Interval' check 'By Month'. Choose January through December")
    print("I: In 'Geographic Area' check 'County' and choose 'Kent'") 
    print("J: Click 'View CSV Report' to download the report. Wait until the download is finished before proceeding.")
    print("K: Nagivate to your computer's downloads folder, where you will find the report you just downloaded.")
    print("L: Click the report once to select it in the folder, then click 'Copy path' in the upper left of the folder")
    print("")
    check = False 
    while check == False:    
        file = input("L: Paste the filepath here: ")
        df = pd.read_csv(to_raw(file).strip('"'))
    
        if str(find_settings(df)) != str(M_DGroup.get_settings()):
            print("Your report doesn't match the correct settings. Please try again")   
        else:
            print("Nice!")
            print('')
            print('___________________________________________________________________')
            check = True
    df = df_cleaning_preprocessing(df)
    return(df)


def option_gui(main, options):
    """
    Starter user-interface GUI
    """
    root = Tk()
    root.geometry('750x800')
    clicked = StringVar()
    clicked.set(options[0])
    Label(root, text='DISEASES').pack()
    label = Label(root, text = [str(a) + '\n' for a in main])
    label.pack()
    OptionMenu(root, clicked, *options).pack()
    def add():
        main.append(clicked.get())
        label.config(text=[str(a) + '\n' for a in main])
    def remove():
        main.remove(clicked.get())
        label.config(text= [str(a) + '\n' for a in main])


    Button(root, text = 'Add to List',command=add).pack()
    Button(root, text = 'Remove from List',command=remove).pack()
    Button(root, text="I'm done!", command=root.destroy).pack()
     
    root.mainloop()

    return main


Investigation_options = SETTING_OPTIONS['Investigation Status']
Case_options = SETTING_OPTIONS['Case Status']

Disease_options = [

    'Giardiasis',
    'Hepatitis C, Acute',
    'Hepatitis C, Chronic',
    'Meningococcal Disease',
    'West Nile Virus',
    'Meningitis - Bacterial Other',
    'Pertussis',
    'Legionellosis',
    'Mumps',
    'Lyme Disease',
    'Novel Coronavirus COVID-19',
    'Streptococcus pneumoniae, Drug Resistant',
    'Hepatitis A',
    'AIDS, Aggregate',
    'Hepatitis B, Acute',
    'H. influenzae Disease - Inv.',
    'Meningitis - Aseptic',
    'Streptococcal Dis, Inv, Grp A',
    'Hepatitis C, Unknown*',
    'Tuberculosis',
    'Campylobacter',
    'Chickenpox (Varicella)',
    'Cryptococcosis',
    'Influenza-Like Illness',
    'Salmonellosis',
    'Shiga toxin-producing Escherichia coli (STEC)',
    'Shigellosis',
    'Syphilis - Secondary',
    'Syphilis - Congenital',
    'Syphilis - Primary',
    'Gonorrhea',
    'Chlamydia (Genital)'
]
    
def check_config():
    """
    Runs through config file to check for any neccesary changes
    Prompts user for changes
    """

    with open('config.json','r') as f:
        file = json.load(f)

    for i in file['groups']:
        print('')
        print("Last month's settings: ")
        print('')
        print("Diseases: " + str(i['diseases']))
        print('')
        print("Case Status: " + str(i['settings']['Case Status']))
        print('')
        print("Investigation Status: " + str(i['settings']['Investigation Status']))
        print('')
        while to_bool(input("Do you need to make any changes? y/n: ")) == True:
            if to_bool(input("Change the list of diseases? y/n: ")) == True:
                i['diseases'] = option_gui(i['diseases'], Disease_options)
            if to_bool(input("Change case status settings? y/n: ")) == True:
                i['settings']['Case Status'] = option_gui(i['settings']['Case Status'], Case_options)
            if to_bool(input("Change investigation status settings? y/n: ")) == True:
                i['settings']['Investigation Status'] = option_gui(i['settings']['Investigation Status'], Investigation_options)
            print('')
            print("Edited Settings: ")
            print('')
            print("Diseases: " + str(i['diseases']))
            print('')
            print("Case Status: " + str(i['settings']['Case Status']))
            print('')
            print("Investigation Status: " + str(i['settings']['Investigation Status']))
            print('')
        print('')
        print("Done!")
        print("_____________________________________________________________________________")



    f = open('config.json','w')
    json.dump(json.loads(json.dumps(file)), f, indent=4)
    f.close()
    
