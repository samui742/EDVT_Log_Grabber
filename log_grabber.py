import re
import requests
import pyautogui
from art import text2art
import os

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

def extract_uut(html):
    """extract uut list from html page"""

    uut_match = re.findall(r'UUT\d+ </span></td>', html)
    uut_list = []

    for match in uut_match:
        uut_id = re.search(r'\d+', match).group(0)
        if uut_id not in uut_list:
            uut_list.append(uut_id)
    return uut_list

def extract_corner(html):
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

def parse_corners(corner_list, corner_select):
    """To create a new corner list from the list of corner that user selected"""

    corner_map = []
    corner_select = [x.strip() for x in corner_select.split(",")]

    for item in corner_select:
        corner_map.append(corner_list[int(item) - 1]) # call value from corner_list by index

    return corner_map

def parse_uuts(uut_list, uut_select):
    """To create a new uut list from the list of corner that user selected"""

    uut_map = []
    uut_select = [x.strip() for x in uut_select.split(",")]

    for item in uut_select:
        if item in uut_list:
            uut_map.append(int(item))

    return uut_map

def grab_switch_logs():
    """ Make a http request for switch log from tt3"""

    url = f"https://wwwin-testtracker3.cisco.com/trackerApp/oneviewlog/switch{uut}.log?page=1&corner_id={corner}"

    response = requests.get(url, auth=(username, password))
    response.close()
    html_log = response.text

    try:
        # content = html_log[html_log.index("Total testcases to execute"):html_log.index("Corner - runSwitch")]
        content = html_log[html_log.index("Total testcases to execute"):html_log.index("/tmp/tt3")]

        corner_name_match = re.findall(r'cornerName :.*', html_log)
        corner_name_match = "".join(corner_name_match)
        corner_name = re.search(r': .*', corner_name_match).group(0).strip(': ').strip('Test').rstrip(" ")

    except ValueError:
        content = "unit " + str(uut) + (" log file was not found due to incomplete corner or unit is a link partner. Please check.")
        # print(f"{bcolors.BOLD}{bcolors.FAIL}log file was not found due to incomplete corner or unit is a link partner. Please check.{bcolors.ENDC}")
        corner_name = "Incomplete"
        # raise SystemExit

    return content, url, corner_name

def switch_log_request():
    """Request logs from tt3 then search for the keywords line by line
    then print out on the console and also write into a text file"""

    jobid_list = extract_user_input(jobids)

    global jobid
    for jobid in jobid_list:
        url = f"https://wwwin-testtracker3.cisco.com/trackerApp/cornerTest/{jobid}"
        response = requests.get(url, auth=(username, password))
        response.close()
        html = response.text

        global total_corner_list
        global total_uut_list
        global len_corner

        total_corner_list = extract_corner(html)
        total_uut_list = extract_uut(html)
        len_corner = len(total_corner_list)

        selected_corner_list, selected_uut_list = user_selection()

        # print(f'selected_uut_list is {selected_uut_list}')

        global uut
        for uut in selected_uut_list:
            print(f'Processing switch{uut}....')
            result_file = f"{jobid}_uut{uut}_{option}_result.txt"
            with open(result_file, "w") as result_file:
                # for corner in corner_list:
                global corner
                for corner in selected_corner_list:
                    content, url, corner_name = grab_switch_logs()
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

def user_selection ():
    """ To offer user on selecting corner and uut to process then returned the selected list to process"""

    selected_corner_list = []
    selected_uut_list = []

    print(f'\nJOBID# {jobid} has total {len(total_corner_list)} corner(s)' + ' - Corner number: ',
          ','.join(map(str, range(1, len_corner + 1))))
    corner_select = input(f'Press enter to search on all corners or specify corner number (using comma if there are '
                          f'multiples): ')
    print()

    if len(corner_select) == 0:
        print(f'\tuser selected all corners\n')
    else:
        print(f'\tuser selected corner {corner_select}\n')

    print(f'JOBID# {jobid} has total {len(total_uut_list)} unit(s)' + ' - Unit number: ', ','.join(map(str, total_uut_list)))
    uut_select = input(
        f'Press enter to search on all units or specify unit number (using comma if there are multiples): ')
    print()

    if len(uut_select) == 0:
        print(f'\tuser selected all units\n')
    else:
        print(f'\tuser selected unit {uut_select}\n')

    # Mapping between total and user selected
    if len(corner_select) == 0:
        selected_corner_list = total_corner_list
    else:
        corner_select = [x.strip() for x in corner_select.split(",")]
        for item in corner_select:
            selected_corner_list.append(total_corner_list[int(item) - 1])  # call value from corner_list by index

    # print(f'user selected unit {uut_select} after mapped with total_uut_list {total_uut_list}')
    if len(uut_select) == 0:
        selected_uut_list = total_uut_list
    else:
        uut_select = [x.strip() for x in uut_select.split(",")]
        for item in uut_select:
            # print(f'{item} item in uut_select list')
            if item in total_uut_list:
                selected_uut_list.append(int(item))

    # print(f'selected_uut_list is {selected_uut_list}')
    return selected_corner_list, selected_uut_list

def extract_user_input (jobids):
    """function to covert input from user into lists"""

    global jobid_list
    global keyword_list

    jobid_list = []

    if "," in str(jobids):
        jobid_list.extend(jobids.split(','))
        jobid_list = [item.strip() for item in jobid_list]
    else:
        jobid_list.append(str(jobids))

    keyword_list = []
    if "," in str(keywords):
        keyword_list = keywords.split(',')
        keyword_list = [item.strip() for item in keyword_list]
    else:
        keyword_list.append(str(keywords).strip())

    # Add to support comma search. User has to input as semicolon
    for i in range(len(keyword_list)):
        if ";" in keyword_list[i]:
            x = keyword_list[i].replace(";", ",")
            keyword_list[i] = x

    return jobid_list


def extract_command_input (command_user):
    """function to covert input from user into lists"""

    global command_list

    command_list = []

    if "," in str(command_user):
        command_list.extend(command_user.split(','))
        command_list = [item.strip() for item in command_list]
        command_list = ["command is : {" + item for item in command_list]
    else:
        command_list.append("command is : {" + str(command_user))

    return command_list

def diag_sfp_report():

    jobid_list = extract_user_input(jobids)

    global jobid
    for jobid in jobid_list:
        sfp_type_result = []
        url = f"https://wwwin-testtracker3.cisco.com/trackerApp/cornerTest/{jobid}"
        response = requests.get(url, auth=(username, password))
        response.close()
        html = response.text

        global total_corner_list
        global total_uut_list
        global len_corner

        total_corner_list = extract_corner(html)
        total_uut_list = extract_uut(html)
        len_corner = len(total_corner_list)

        selected_corner_list, selected_uut_list = user_selection()
        global uut
        for uut in selected_uut_list:
            sfp_file_result = f'{jobid}_switch{uut}_sfp_result.txt'
            with open(sfp_file_result, "w") as sfp_file_result:

                global corner
                global sfpeeprom_csv_file
                for corner in selected_corner_list:
                    sfpeeprom_csv_file = sfp_tt3_log_request()
                    list_of_port_dict, sfp_type_result = create_list_dict_sfp()
                    print(f"\nPROCESSING ON JOBID: {jobid} CORNERID: {corner} UNIT: {uut}")
                    fail_port_single, url, serial_number = check_sfp_diag_traffic()
                    print_sfp_result(list_of_port_dict, fail_port_single, sfp_file_result, jobid, corner, uut, url, serial_number)
                print_sfp_summary(jobid, uut, sfp_type_result, sfp_file_result)
            sfp_file_result.close()

def sfp_tt3_log_request():
    """Retrieve SFP data from the user-provided jobID list by making a request to TT3 \
    then filter out all the unnecessary text then print out the table format"""

    file_list = []

    url = f"https://wwwin-testtracker3.cisco.com/trackerApp/oneviewlog/opticalData.csv?page=1&corner_id={corner}"
    response = requests.get(url, auth=(username, password))
    response.close()
    html = response.text

    # Strip out space and double space
    lines = (line.strip() for line in html.splitlines())
    # Fix strange character from various sfp type
    lines = (line.replace("  (", " (") for line in lines)
    lines = (line.replace("],", ",") for line in lines)
    lines = (line.replace(",INC,", ",") for line in lines)
    lines = (line.replace(",0x10  -- unrecognized compliance code.,", ",0x10 unrecognized,") for line in lines)
    chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
    text = '\n'.join(chunk for chunk in chunks if chunk)

    # Strip off unnecessary text but keep SFPEEPROM data table
    stri = text[text.index('+++'):text.index('Show\n')]
    sections = re.split(r"\s*\+{10,}\s*", stri)
    # To strip blank element
    section_headers = [section.strip() for section in sections if section.strip()]

    for header in section_headers[::2]:
        # Generate CSV file for SFEEPROM only
        if header == "SFEEPROM":
            sfpeeprom_csv_file = f"{jobid}_{corner}_{header}.csv"
            file_list.append(sfpeeprom_csv_file)

    # Map header and date into the generated csv file
    # writing sfp table  into a csv file
    for header, section_data in zip(section_headers[::2], section_headers[1::2]):
        for i in range(0, len(file_list)):
            if header in file_list[i]:
                # print('separating', header, 'table into a file')
                # file = open(file_list[i], "a")
                file = open(file_list[i], "w")
                file.write('+' * 35 + ' ' + header + ' ' + '+' * 35 + '\n')
                file.write(section_data)
                file.close()
    file_list = []
    return sfpeeprom_csv_file

def create_list_dict_sfp():

    sfp_type_result = []

    with open(sfpeeprom_csv_file, 'r') as input_file:
        lines = input_file.readlines()
        lines = lines[2:]

    list_of_port_dict = []
    for line in lines:
        # if "switch" + str(unit) in line:
        if "switch" + str(uut) in line:
            s = {}
            (s["jobid"], s["cornerid"], s["uut"], s["port"], s["type"], s["vendor"], s["mfg"], s["sn"], s["create"],
             s["create_date"], s["update"], s["update_date"], s["slot"]) = line.split(",")

            # To add s["pid"] here
            # add a function to find pid from mfg number
            s["pid"] = find_pid_by_mfg(s["mfg"])
            s["port"] = s["port"].zfill(2)

            # This part is database mapping to find out type from mfg partnumber
            if s["type"] == "Data unavailable" or s["type"] == "0x0 (Non Standard)" or s["type"] == "0x80 (Unknown)" or \
                    s["type"] == "0x10 unrecognized":
                s["type"] = find_type_by_mfg(s["mfg"])
            else:
                s["type"] = re.search(r"\((.*?)\)", s["type"]).group(1)
                # TRY OVERWRITE TYPE IF MFG AVAILABLE IN DATABASE
                s["type"] = find_type_by_mfg(s["mfg"])

            if (s['type'], s['vendor'], s['mfg'], s['pid']) not in sfp_type_result:
                sfp_type_result.append((s['type'], s['vendor'], s['mfg'], s['pid']))

            s["vendor"] = find_vendor_by_mfg(s["mfg"])
            list_of_port_dict.append(s)

    input_file.close()
    os.remove(sfpeeprom_csv_file)
    return list_of_port_dict, sfp_type_result

def find_type_by_mfg(lookup_mfg):
    input_file = open('SFPs_Database.csv')
    for line in input_file:
        data = {}
        (data['type'], data['vendor'], data['mfg'], data['pid'], data['sn']) = line.split(',')
        if data['mfg'] == lookup_mfg:
            input_file.close()
            return data["type"]
    input_file.close()
    return "Not in Database"

def find_pid_by_mfg(lookup_mfg):
    input_file = open('SFPs_Database.csv')
    for line in input_file:
        data = {}
        (data['type'], data['vendor'], data['mfg'], data['pid'], data['sn']) = line.split(',')
        if data['mfg'] == lookup_mfg:
            input_file.close()
            return data["pid"]
    input_file.close()
    return "Not in Database"

def find_vendor_by_mfg(lookup_mfg):
    input_file = open('SFPs_Database.csv')
    for line in input_file:
        data = {}
        (data['type'], data['vendor'], data['mfg'], data['pid'], data['sn']) = line.split(',')
        if data['mfg'] == lookup_mfg:
            input_file.close()
            return data["vendor"]
    input_file.close()
    return "Not in Database"

def extract_total_uut(html):
    uut_match = re.findall(r'UUT\d+ </span></td>', html)
    total_uut = []

    for match in uut_match:
        uut_id = re.search(r'\d+', match).group(0)
        if uut_id not in total_uut:
            total_uut.append(uut_id)
    return total_uut

def extract_total_corner(html):
    corner_match = re.findall(r'data-cornerid="\d+"', html)
    total_corner = []

    for match in corner_match:
        corner_id = re.search(r'\d+', match).group(0)
        if corner_id not in total_corner:
            total_corner.append(corner_id)
    return total_corner

def print_sfp_result(list_of_port_dict, failed_port_single, sfp_file_result, jobid, corner, uut, url, serial_number):
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

    print(f'\nJobID:{jobid} CornerID:{corner} switch:{uut} {serial_number}\n{url}')
    sfp_file_result.write('\n' + f'JobID:{jobid} CornerID:{corner} switch:{uut} {serial_number}\n{url}\n' )
    print(f'{bcolors.BOLD}{bcolors.OKBLUE}-{bcolors.ENDC}' * 150)
    sfp_file_result.write('-' * 150 + '\n')

    print(f'{bcolors.BOLD}{bcolors.OKBLUE}{"port":<10} {"sfp_type":<20} {"Cisco PID":<20} {"sfp_vendor":<20} {"mfg_number":<20} {"serial_number":<20} {"port_result"}{bcolors.ENDC}')
    sfp_file_result.write(f'{"port":<10} {"sfp_type":<20} {"Cisco PID":<20} {"sfp_vendor":<20} {"mfg_number":<20} {"serial_number":<20} {"port_result"}' + '\n')
    print(f'{bcolors.BOLD}{bcolors.OKBLUE}-{bcolors.ENDC}' * 150)
    sfp_file_result.write('-' * 150+ '\n')

    list_of_port_dict = sorted(list_of_port_dict, key=lambda k: k['port'])

    for item in list_of_port_dict:
        item.update(port_result="pass")

        for failed_port in failed_port_single:
            if item["port"] == failed_port:
                item.update(port_result="fail")

        if item["port_result"] == "fail":
            print(
                f'{bcolors.FAIL}{item["port"].strip("]"):<10} {item["type"]:<20} {item["pid"]:<20} {item["vendor"]:<20} {item["mfg"]:<20} {item["sn"]:<20} {item["port_result"]:<20}{bcolors.ENDC}')
            sfp_file_result.write(f'{item["port"].strip("]"):<10} {item["type"]:<20} {item["pid"]:<20} {item["vendor"]:<20} {item["mfg"]:<20} {item["sn"]:<20} {item["port_result"]} ***' + "\n")
        else:
            print(
                f'{bcolors.OKGREEN}{item["port"].strip("]"):<10} {item["type"]:<20} {item["pid"]:<20} {item["vendor"]:<20} {item["mfg"]:<20} {item["sn"]:<20} {item["port_result"]:<20}{bcolors.ENDC}')
            sfp_file_result.write(f'{item["port"].strip("]"):<10} {item["type"]:<20} {item["pid"]:<20} {item["vendor"]:<20} {item["mfg"]:<20} {item["sn"]:<20} {item["port_result"]:<20}' + '\n')

def check_sfp_diag_traffic():

    result = []
    url = f"https://wwwin-testtracker3.cisco.com/trackerApp/oneviewlog/switch{uut}.log?page=1&corner_id={corner}"

    response = requests.get(url, auth=(username, password))
    response.close()
    html_log = response.text

    html_log_name = f"{jobid}_{corner}_uut{uut}_html_log.txt"
    data = {"cornerid": corner, "uut": uut, "logfile": html_log_name, "failures": [], "uutinfo": []}
    result.append(data)
    content = html_log[html_log.index("TESTCASE START"):html_log.index(f"{corner} Complete")]

    # To add option if need a local html log
    with open(html_log_name, "w") as local_log:
        local_log.write(content)

    for item in result:
        f = open(item["logfile"], "r")
        text = f.read()
        content = text[text.index("TESTCASE START"):text.index("Corner - runSwitch")]
        lines = content.splitlines()
        for line in lines:
            if "SYSTEM_SERIAL_NUM" in line:
                if line not in item['uutinfo']:
                    item['uutinfo'].append(line.strip())

            # SEARCH FOR FAILED PORTS
            if re.search(r'FAIL\*\*\s+[a-zA-Z]', line):
                data = {}
                if line not in item['failures']:
                    item['failures'].append(line)
        f.close()
    os.remove(item["logfile"])

    # Find failed traffic combination
    traf_failures = []
    traffic_failed_combination_list = []

    for item in result:
        switch_number = 'switch' + str(item['uut'])

        for info in item['uutinfo']:
            if "SYSTEM_SERIAL" in info:
                serial_number = info
                # print(f"{serial_number}")

        for failure in item['failures']:
            # print(failure)
            if "Ext" in failure:
                data = {}
                (data['conver'], data['portpair'], data['iter'], data['duration'], data['status'], data['error'],
                 data['duration'], data['portresult'], data['traftype'], data['speed'], data['size']) = failure.split()
                traf_failures.append(data)

    for item in traf_failures:
        for key in ["conver", "iter", "duration", "status", "portresult"]:
            item.pop(key)
        if item not in traffic_failed_combination_list:
            traffic_failed_combination_list.append(item)

    # Find failed portpair and convert into single port list
    fail_portpair = []
    fail_port_single = []
    for item in traffic_failed_combination_list:
        if item["portpair"] not in fail_portpair:
            fail_portpair.append(item["portpair"])

            # To create a new list with a single port to map with the SFP list in the future
            first_port, second_port = item["portpair"].split('/')
            if first_port not in fail_port_single or second_port not in fail_port_single:
                fail_port_single.append(first_port.zfill(2))
                fail_port_single.append(second_port.zfill(2))
    fail_port_single.sort()

    # Find failed speeds - for future report
    fail_speed = []
    for item in traffic_failed_combination_list:
        if item["speed"] not in fail_speed:
            fail_speed.append(item["speed"])
    # print("failed speeds are : ", *fail_speed, sep='\n\t')

    # Find failed sizes - for future report
    fail_size = []
    for item in traffic_failed_combination_list:
        if item["size"] not in fail_size:
            fail_size.append(item["size"])
    # print("failed size are : ", *fail_size, sep='\n\t')

    return fail_port_single, url, serial_number

def print_sfp_summary(jobid, uut, sfp_type_result, sfp_file_result):

    print("\n--------------------------------------------")
    sfp_file_result.write("\n--------------------------------------------\n")
    print(f"SUMMARY : JOBID {jobid} SWITCH{uut} THERE ARE TOTAL {len(sfp_type_result)} VARIATIONS OF SFPS")
    sfp_file_result.write(f"SUMMARY : JOBID {jobid} SWITCH{uut} THERE ARE TOTAL {len(sfp_type_result)} VARIATIONS OF SFPS\n")
    print("--------------------------------------------")
    sfp_file_result.write("--------------------------------------------\n")

    print(f'NO,TYPE,PID,VENDOR,MFG_PARTNUM')
    sfp_file_result.write(f'NO,TYPE,PID,VENDOR,MFG_PARTNUM\n')

    for index, item in enumerate(sfp_type_result, 1):
        item_list = list(item)
        print(f'{index},{item_list[0]},{item_list[3]},{item_list[1]},{item_list[2]}')
        sfp_file_result.write(f'{index},{item_list[0]},{item_list[3]},{item_list[1]},{item_list[2]}' + '\n')


def command_output_request(jobids_input, command_user, username, password, option):

    jobid_list = extract_user_input(jobids)
    command_list = extract_command_input(command_user)
    # print("command_list", command_list)

    global jobid
    for jobid in jobid_list:
        url = f"https://wwwin-testtracker3.cisco.com/trackerApp/cornerTest/{jobid}"
        response = requests.get(url, auth=(username, password))
        response.close()
        html = response.text

        global total_corner_list
        global total_uut_list
        global len_corner

        total_corner_list = extract_corner(html)
        total_uut_list = extract_uut(html)
        len_corner = len(total_corner_list)

        selected_corner_list, selected_uut_list = user_selection()
        global uut
        for uut in selected_uut_list:
            result_file = f'{jobid}_switch{uut}_{command_user}_result.txt'
            with open(result_file, "w") as result_file:
                global corner
                for corner in selected_corner_list:
                    for command in command_list:
                        # print("command", command)
                        # print(f"searching command = {command} .....")
                        # command = "command is : {" + command
                        start_list = []
                        stop_list = []
                        content, url, corner_name = grab_switch_logs()
                        lines = content.splitlines()

                        print("\n" + "="*100)
                        print(f'jobid= {jobid} cornerid= {corner} cornername= {corner_name} unit= switch{uut}')
                        print("Searched Command = ", command)
                        print(f'{url}')
                        print("="*100)
                        result_file.write("="*100 + "\n")
                        result_file.write(f'jobid= {jobid} cornerid= {corner} cornername= {corner_name} unit= switch{uut}' + "\n")
                        result_file.write(f"Searched Command = , {command}" + "\n")
                        result_file.write(f"URL: {url}" + "\n")
                        result_file.write("="*100 + "\n")

                        # To specify stop point of each command output
                        # TT3 might change the print out which will affect the code here
                        stop_keyword = "command is :"
                        stop_keyword_2 = "Corner - runSwitch"
                        stop_keyword_3 = f"FAIL_FLAG FROM EDVT_CSVPARSE FOR COMMAND"
                        lines = content.split('\n')
                        for i in range(len(lines)):
                            if command in lines[i]:
                                start_list.append(i)

                        # START SEARCHING FOR STOP POINT FROM WHERE THE COMMAND IS FOUND THEN BREAK ONCE FOUND
                        for item in start_list:
                            for i in range(item + 1, len(lines)):
                                if stop_keyword in lines[i] or stop_keyword_2 in lines[i] or stop_keyword_3 in lines[i]:
                                    stop_list.append(i)
                                    break

                        # MAPPING BETWEEN START AND STOP POINT LIST
                        mapped = list(zip(start_list, stop_list))

                        # WRITE RESULT INTO TEXT FILE
                        command_output = []
                        for count, (command_user_index, stop_keyword_index) in enumerate(mapped, 1):
                            if option != "bert_diag":
                                print(f"\n################################################## {command.upper().strip('command is : {')} OUTPUT FOUND # {count} ##################################################\n")
                                result_file.write(f"\n################################################## {command.upper().strip('command is : {')} OUTPUT FOUND # {count} ##################################################\n")

                            for line in lines[command_user_index - 1:stop_keyword_index + 1]:
                                if option != "bert_diag":
                                    print("\t\t" + line)
                                    result_file.write("\t\t" + line + "\n")
                                if option == "bert_diag":
                                    command_output.append(line)

                        # print(*command_output, sep='\n')
                        if option == "bert_diag":
                            # find index of the start and stop line of bershowresult command then append into a list
                            header = " P#     Transmit      TxBytes    TxColFcs Receive       RxBytes      RxFcs Align RxCol OvrSz UndSz RxSym OvRun"
                            footer = "Traf&gt; *****************************************************************************************************************"


                            # TO REMOVE HEADER FOOTER
                            new_list = []
                            for i in range(len(command_output)):
                                if header in command_output[i]:
                                    header_index = i
                                    new_list.append(header_index)
                                if footer in command_output[i]:
                                    footer_index = i
                                    new_list.append(footer_index)
                            # print(*new_list)

                            # pair start and stop index in the list so we can process each bershowresult output at a time
                            pair_list = []
                            for i in range(len(new_list)):
                                if i % 2 == 0:
                                    pair_list.append((new_list[i], new_list[(i + 1) % len(new_list)]))

                            # print(*pair_list)
                            # print("==" * 100 + "\n" + "SUMMARY OF FAILED PORTS" + "\n" + "==" * 100)
                            print("\n\t" + "SUMMARY OF FAILED PORTS" + "\n\t" + "-" * 100)

                            # print("command_output", *command_output, sep='\n')
                            # print("new_list", *new_list, sep='\n')

                            for index, item in enumerate(pair_list, 1):
                                # print("==" * 100 + "\n" + f"{command} output number #" + str(index) + "\n", item)
                                print("\n" + "\t\t" + f"{command.strip('command is : {')} output number #" + str(index))
                                print("\t\t" + "==" * 50)
                                (p1, p2) = item
                                # print(*lines[p1:p2], sep='\n')
                                focus_input = command_output[p1:p2]
                                focus_input.pop(1)
                                focus_input.pop(-1)
                                focus_input.pop(-1)
                                # focus_input = [item.strip() for item in focus_input]

                                # print(*focus_input, sep='\n')
                                # print(len(focus_input))

                                s = {}
                                port_list = []
                                for x in range(len(focus_input)):
                                    f = focus_input[x].strip()
                                    f = " ".join(focus_input[x].split())
                                    l = f.split()
                                    # print(x)
                                    # print(l)

                                    # print(focus_input[i])
                                    # (*other, s["Port"], s["Transmit"], s["TxBytes"], s["TxErr"], s["Receive"], s["RxBytes"], s["RxFcs"], s["RxIpg"],
                                    #  s["RxCol"], s["OvrSz"], s["UndSz"], s["RxSym"], s["OvRun"]) = l

                                    (*other, port, transmit, txbytes, txerr, receive, rxbytes, rxfcs, rxipg,
                                     rxcol, ovsz, undsz,
                                     rxsym, ovrun) = l

                                    # print(s["Port"])
                                    port = port.strip("*")
                                    # print(port)
                                    port_list.append(port)

                                    # if port == "15":
                                    #     print(focus_input[x])

                                    zero = "00000"
                                    if rxfcs != zero or rxipg != zero or rxcol != zero or ovsz != zero or undsz != zero or rxsym != zero or ovrun != zero:
                                        print("\t\t\t" + focus_input[x])

                                port_list.pop(0)
                                # print(port_list)

            result_file.close()

############ MAIN ################

if __name__ == '__main__':

    global username
    global password
    global jobids
    global option
    global keywords

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
    4 - diag sfp summary "generate sfp summary by using output from opticaltest to map with edvt database"\n\
    5 - search specific command output "user can specific the command(s) that user would like to see the output\n\
    6 - bert diag ixia\n\
    Please enter the option number: ')



    if options == "1":
        option = "keyword_search"
        keywords = input("Enter keywords separate by comma: ")
        switch_log_request()

    elif options == "2":
        option = "diag_traffic"
        keywords = "FAILED VALIDATION while, FAILED VALIDATION -, FAIL**  E, FAIL**  P, TESTCASE START -, Test(s) failed:"
        switch_log_request()

    elif options == "3":
        option = "istardust_traffic"
        keywords = "TESTCASE START -, FAILED VALIDATION while, FAILED VALIDATION -, Pass Fail, Fail Pass, Fail Fail, Status: Failed, ERROR DOYLE_FPGA, FAILED: Timeout,  ERROR: Leaba_Err"
        switch_log_request()

    elif options == "4":
        option = "diag_sfp_summary"
        keywords = "FAILED VALIDATION while, FAILED VALIDATION -, FAIL**  E, FAIL**  P, TESTCASE START -"
        diag_sfp_report()

    elif options == "5":
        option = "command_output"
        command = input("Enter the command: ")
        # command = "command is : {" + command
        keywords = "FAILED VALIDATION while, FAILED VALIDATION -, FAIL**  E, FAIL**  P, TESTCASE START -"
        command_output_request(jobids, command, username, password, option)

    elif options == "6":
        option = "bert_diag"
        command = "bershowresult"
        keywords = "FAILED VALIDATION while, FAILED VALIDATION -, FAIL**  E, FAIL**  P, TESTCASE START -"
        command_output_request(jobids, command, username, password, option)


