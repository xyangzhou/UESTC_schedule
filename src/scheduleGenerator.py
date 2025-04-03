from collections import defaultdict
import time
from typing import Any, Dict, List, Optional, Tuple, Union
import requests
from tqdm import tqdm
from tools.UESTC_login import UESTC_login


class scheduleGenerator:
    def __init__(self, termInfoUrl:str, weekInfoUrl:str, *, 
                 data: Dict[str, Any], headers: Dict[str, Any], 
                 cookies: Optional[str]=None, 
                 username: Optional[str]=None, password: Optional[str]=None, 
                 cas_baseurl: Optional[str]=None, cas_header: Optional[Dict[str, Any]]=None) -> None:
        self.username = username
        self.password = password
        self.data = data
        self.cookies = cookies
        self.session = requests.Session()
        self.headers = headers
        self.maxWeekIndex = -1
        self.termInfoUrl = termInfoUrl
        self.weekInfoUrl = weekInfoUrl
        self.cas_baseurl = cas_baseurl
        self.cas_header = cas_header

        if self.cookies:
            self.headers['Cookie'] = f"eai-sess={self.cookies}"
            self.session.headers.update(self.headers)
        else:
            self.session.headers.update(self.headers)
            self.login()


    def getTermInfo(self, year: str, term: int) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        response = self.session.get(self.termInfoUrl)
        term_info = response.json()['d']['termInfo']

        if response.status_code != 200:
            raise ConnectionError(f"Failed to connect to {self.termInfoUrl}, code: {response.status_code}")
        if response.json()['m'] != '操作成功':
            raise RuntimeError(f"Failed to get timetable, message: {response.json()['d']['m']}")
        
        for info in term_info:
            if info['year'] == year and info['term'] == term:
                self.maxWeekIndex = info['countweek']
                return info, response.json()
        
        raise ValueError(f"Term {year}_{term} not found")
    
    def getWeekInfo(self, week: int) -> Tuple[Dict[str, Any], Dict[str, Any], Dict[str, Any]]:
        if self.maxWeekIndex == -1:
            raise RuntimeError("Max week index not set, call getTermInfo first")
        if week > self.maxWeekIndex:
            print(f"\033[33mWarning: Week index {week} is greater than max week index {self.maxWeekIndex}, set week_index to max week index\033[0m")

        self.data.update({'week': week})

        response = self.session.post(self.weekInfoUrl, data=self.data)

        if response.status_code != 200:
            raise ConnectionError(f"Failed to connect to {self.weekInfoUrl}, code: {response.status_code}")
        if response.json()['m'] != '操作成功':
            raise RuntimeError(f"Failed to get timetable, message: {response.json()['d']['m']}")
        
        return response.json()['d']['classes'], response.json()['d']['weekdays'], response.json()

    def getSchedule(self, year: str, term: int, week: Union[int, List[int]], afk=0.1) -> Dict[int, Dict[str, Dict[str, Any]]]:
        print(f"\033[32mGetting semester info for {year}_{term}\033[0m")
        term_info, _ = self.getTermInfo(year, term)
        print(f"\033[32mSucceesful! Geted info:\033[0m")
        print(term_info)
        self.data.update({
            'year': term_info['year'],
            'term': term_info['term']
        })
        
        if isinstance(week, int):
            if week == -1:
                week = self.maxWeekIndex
                week = [1, week]
            else:
                week = [week, week]

        if week[0] > self.maxWeekIndex:
            print(f"\033[33mWarning: Given week index week[0] {week[0]} is greater than max week index {self.maxWeekIndex}, set week_index to max week index\033[0m")
            week[0] = self.maxWeekIndex
        if week[1] > self.maxWeekIndex:
            print(f"\033[33mWarning: Given week index week[1] {week[1]} is greater than max week index {self.maxWeekIndex}, set week_index to max week index\033[0m")
            week[1] = self.maxWeekIndex

        weeks = range(week[0], week[1] + 1)
        
        print(f"\033[32mGetting schedule for weeks:\033[0m")
        print(list(weeks))

        classes, weekdays = {}, {}
        schedule = {}
        for w in tqdm(weeks, desc="Getting weekly schedule"):
            classes, weekdays, _ = self.getWeekInfo(w)
            time.sleep(afk)
            week_schedule = {}
            
            for _cls, wd in zip(classes, weekdays):
                day_schedule = []
                
                for c in _cls.values():
                    day_schedule.extend(c)
                week_schedule[wd] = day_schedule
            
            schedule[w] = week_schedule
        
        return schedule

    def get_login_url(self) -> Tuple[bool, str]:
        response = self.session.get(self.termInfoUrl)
        if response.status_code != 200:
            raise ConnectionError(f"Failed to connect to {self.weekInfoUrl}, code: {response.status_code}")
        
        res_json = response.json()
        if res_json['m'] == '操作成功':
            return False, ''
        else:
            try:
                login_url = res_json['d']['login_url']
            except KeyError:
                raise RuntimeError(f"Failed to get login URL, response: {res_json}")
            
            return True, login_url

    def get_cas_url(self, ori_login_url) -> str:
        response = self.session.get(ori_login_url)
        if response.status_code != 302:
            raise ConnectionError(f"Failed to redirected from {ori_login_url}, code: {response.status_code}")
        
        try:
            login_url = response.headers['X-Redirect']
        except KeyError:
            raise RuntimeError(f"Failed to get login URL, response: {response.json()}")
        login_response = self.session.get(login_url, allow_redirects=False)
        if login_response.status_code != 302:
            raise ConnectionError(f"Failed to redirected from {login_url}, code: {login_response.status_code}")
        
        try:
            cas_url = login_response.headers['Location']
        except KeyError:
            raise RuntimeError(f"Failed to get CAS URL, response: {login_response.json()}")
        if 'idas.uestc.edu.cn' not in cas_url:
            raise RuntimeError(f"Failed to get CAS URL, response: {login_response.json()}")
        
        return cas_url

    def login(self):
        print("\033[32mLogging in...\033[0m")

        need, login_url = self.get_login_url()
        if not need:
            print("\033[33mAlready logged in!\033[0m")
            return
        
        cas_url = self.get_cas_url(login_url)

        login = UESTC_login(self.cas_baseurl, cas_url, self.cas_header)
        _, header = login.login(self.username, self.password)

        server_url_with_st = header['Location']
        print(f"\033[32mRedirecting to {server_url_with_st} with ST token\033[0m")
        response =  self.session.get(server_url_with_st)
        if response.status_code != 302:
            raise ConnectionError(f"Failed to redirected from {server_url_with_st}, code: {response.status_code}")
        try:
            index = response.headers['X-Redirect']
            if 'mapp.uestc.edu.cn' not in index:
                raise RuntimeError(f"Failed to login, response: {response.json()}")
        except KeyError:
            raise RuntimeError(f"Failed to login, response: {response.json()}")
        # self.headers['Cookie'] = f"eai-sess={self.cookies}"
        print("\033[32mLogin successful!\033[0m")
