import re
import requests
import pyautogui
from art import text2art

class bcolors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

def extract_uut_list(html):
    """extract uut list from html page"""

    uut_match = re.findall(r'UUT\d+ </span></td>', html)
    uut_list = []

    for match in uut_match:
        uut_id = re.search(r'\d+', match).group(0)
        if uut_id not in uut_list:
            uut_list.append(uut_id)
    return uut_list

def extract_corner_ids(html):
    """extract corner id list from html page"""

    corner_match = re.findall(r'data-cornerid="\d+"', html)
    corner_list = []
    for match in corner_match:
        corner_id = re.search(r'\d+', match).group(0)
        if corner_id not in corner_list:
            corner_list.append(corner_id)
    return corner_list

def parse_jobids(jobids_input):
    """put multiple jobids from user input into a list"""

    jobid_list = []
    if "," in str(jobids_input):
        jobid_list.extend(jobids_input.split(','))
        jobid_list = [item.strip() for item in jobid_list]
    else:
        jobid_list.append(str(jobids_input))
    return jobid_list

def parse_keywords(keywords_input):
    """put multiple keywords from user input into a list
    if a comma is in keywords, user has to use semicolon to
    separate between keywords instead of comma"""

    keyword_list = []
    if "," in str(keywords_input):
        keyword_list = keywords_input.split(',')
        keyword_list = [item.strip() for item in keyword_list]
    else:
        keyword_list.append(str(keywords_input).strip())

    # Add to support comma search. User has to input as semicolon
    for i in range(len(keyword_list)):
        if ";" in keyword_list[i]:
            x = keyword_list[i].replace(";",",")
            keyword_list[i] = x

    return keyword_list

def parse_corners(corners_list, corner_select):
    """To create a new corner list from the list of corner that user selected"""

    corner_map = []
    corner_select = [x.strip() for x in corner_select.split(",")]

    for item in corner_select:
        corner_map.append(corners_list[int(item) - 1]) # call value from corner_list by index

    return corner_map

def parse_uuts(uut_list, uut_select):
    """To create a new uut list from the list of corner that user selected"""

    uut_map = []
    uut_select = [x.strip() for x in uut_select.split(",")]

    for item in uut_select:
        if item in uut_list:
            uut_map.append(int(item))

    return uut_map

def grab_switch_logs(corner, uut, jobid, username, password):
    """ Make a http request for switch log from tt3"""

    url = f"https://wwwin-testtracker3.cisco.com/trackerApp/oneviewlog/switch{uut}.log?page=1&corner_id={corner}"

    response = requests.get(url, auth=(username, password))
    response.close()
    html_log = response.text

    try:
        content = html_log[html_log.index("Total testcases to execute"):html_log.index("Corner - runSwitch")]
    except ValueError:
        content = "unit " + str(uut) + (" log file was not found due to incomplete corner or unit is a link partner. Please check.")
        print(f"{bcolors.BOLD}{bcolors.FAIL}log file was not found due to incomplete corner or unit is a link partner. Please check.{bcolors.ENDC}")
        raise SystemExit

    corner_name_match = re.findall(r'cornerName :.*', html_log)
    corner_name_match = "".join(corner_name_match)
    corner_name = re.search(r': .*', corner_name_match).group(0).strip(': ').strip('Test').rstrip(" ")

    return content, url, corner_name

def switch_log_request(jobids_input, keywords_input, username, password, option):
    """Request logs from tt3 then search for the keywords line by line
    then print out on the console and also write into a text file"""

    jobid_list = parse_jobids(jobids_input)
    print("\nUser Input jobIDs  = ", jobid_list)
    print()

    keyword_list = parse_keywords(keywords_input)
    print("Keywords to search = ", keyword_list)
    print()

    for jobid in jobid_list:
        url = f"https://wwwin-testtracker3.cisco.com/trackerApp/cornerTest/{jobid}"
        response = requests.get(url, auth=(username, password))
        response.close()
        html = response.text

        corner_list = extract_corner_ids(html)
        uut_list = extract_uut_list(html)
        len_corner = len(corner_list)

        print(f'JOBID# {jobid} has total {len(corner_list)} corner(s)' + ' - Corner number: ', ','.join(map(str, range(1, len_corner + 1))))
        corner_select = input(f'Press enter to search on all corners or specify corner number (using comma if there are '
                              f'multiples): ')
        print()

        if len(corner_select) == 0:
            print(f'\tuser selected all corners\n')
        else:
            print(f'\tuser selected corner {corner_select}\n')

        print(f'JOBID# {jobid} has total {len(uut_list)} unit(s)' + ' - Unit number: ', ','.join(map(str, uut_list)))
        uut_select = input(f'Press enter to search on all units or specify unit number (using comma if there are multiples): ')
        print()

        if len(uut_select) == 0:
            print(f'\tuser selected all units\n')
        else:
            print(f'\tuser selected unit {uut_select}\n')

        if len(corner_select) == 0:
            pass
        else:
            corner_list = parse_corners(corner_list, corner_select)

        if len(uut_select) == 0:
            pass
        else:
            uut_list = parse_uuts(uut_list, uut_select)

        for uut in uut_list:
            result_file = f"{jobid}_uut{uut}_{option}_result.txt"
            with open(result_file, "w") as result_file:
                for corner in corner_list:
                    content, url, corner_name = grab_switch_logs(corner, uut, jobid, username, password)
                    # Process content starts from here
                    if len(keywords) != 0:
                        print("="*100)
                        print(f'jobid= {jobid} cornerid= {corner} cornername= {corner_name} unit= switch{uut}')
                        print("Searched Keyword(s) = ", keyword_list)
                        print(f'{url}')
                        print("="*100)
                        result_file.write("="*100 + "\n")
                        result_file.write(f'jobid= {jobid} cornerid= {corner} cornername= {corner_name} unit= switch{uut}' + "\n")
                        result_file.write(f"Searched Keyword(s) = , {keyword_list}" + "\n")
                        result_file.write(f"URL: {url}" + "\n")
                        result_file.write("="*100 + "\n")
                        lines = content.splitlines()
                        line_with_keyword_list = []

                        for line in lines:
                            # To handle crashed corner
                            if f'REMOVING switch{uut} FROM CURRENT CORNER - JOB' in line:
                                print(f'{bcolors.BOLD}{bcolors.WARNING} *** Corner is NOT completed, switch is removed from the current corner ***{bcolors.ENDC}')
                                result_file.write(
                                    '\nCorner is NOT completed, switch is removed from the current corner\n\n')
                            # To handle link partner unit which does not have log file
                            if "log file was not found due to incomplete corner or unit is a link partner. Please check" in line:
                                print(f'{bcolors.BOLD}{bcolors.WARNING}*** {line} ***{bcolors.ENDC}')
                                result_file.write(line + "\n")

                            for keyword in keyword_list:
                                if keyword in line:
                                    line_with_keyword_list.append(line)
                                    # To display testcase names on the report
                                    if "TESTCASE START" in line:
                                        print("\t" + f'{bcolors.OKBLUE}{line}{bcolors.ENDC}')
                                        result_file.write("\t" + line + "\n")
                                    else:
                                        print("\t\t\t" + f'{bcolors.FAIL}{line}{bcolors.ENDC}')
                                        result_file.write("\t\t\t" + line + "\n")
            result_file.close()

############ MAIN ################

if __name__ == '__main__':

    banner = text2art("EDVT \nLog Scrubber", space=1)
    print("\n" + banner + "\n")

    print('Enter CEC username and password in the popup window \n')

    username = pyautogui.prompt('input your cec username: ')
    password = pyautogui.password('input your password: ')
    if len(username) == 0 or len(password) == 0:
        print("Username and Password can't be blank. Please restart the program")
        quit()

    jobids = input("Enter JOBID (separate by comma for multiples): ")
    options = input(f'\nSelect from options below \n\
    \n\
    1 - search by keywords "user can specify multiple keywords" \n\
    2 - diag traffic failure "a set of pre-defined keywords specifically for diag traffic log scrubbing"\n\
    3 - istardust diag traffic failure "a set of pre-defined keywords specifically for istardust traffic log scrubbing"\n\
    \n\
    Please enter the option number: ')

    if options == "1":
        # keywords = " MODEL_NUM,  SYSTEM_SERIAL, Test(s) failed:, test(s) failed"
        option = "keyword_search"
        keywords = input("Enter keywords separate by comma: ")
        switch_log_request(jobids, keywords, username, password, option)

    elif options == "2":
        option = "diag_traffic"
        keywords = "FAILED VALIDATION while, FAILED VALIDATION -, FAIL**  E, FAIL**  P, TESTCASE START -, Test(s) failed:"
        switch_log_request(jobids, keywords, username, password, option)

    elif options == "3":
        option = "istardust_traffic"
        keywords = "TESTCASE START -, FAILED VALIDATION while, FAILED VALIDATION -, Pass Fail, Fail Pass, Fail Fail, Status: Failed, ERROR DOYLE_FPGA, FAILED: Timeout,  ERROR: Leaba_Err"
        switch_log_request(jobids, keywords, username, password, option)