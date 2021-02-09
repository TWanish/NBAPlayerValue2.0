#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script for Scraping NBA Player Data. This is my personal hell.

@author: TWanish
"""

import requests, bs4, json, time

"""Gathering List of Players Active Between Year Start and Year End"""

base_player_list_url = 'https://www.basketball-reference.com/players/'
year_start = 2012
year_end = 2021
player_list=[]

for i in range(ord('a'), ord('z')):  #a-z char codes 
    
    player_list_url = f'{base_player_list_url}{chr(i)}'
    res = requests.get(player_list_url)
    html = res.content
    soup = bs4.BeautifulSoup(html, 'html.parser')
    player_table = soup.find('div',attrs={'id':'div_players'}).contents[1]
    rows = player_table.findAll('tr')
    
    for j in range(1,len(rows)):
        
        min_player_year = int(rows[j].findAll('td')[0].string)
        max_player_year = int(rows[j].findAll('td')[1].string)
        
        if (year_start <= min_player_year <= year_end or 
            year_start <= max_player_year <= year_end):
            player_name = rows[j].findAll('th')[0].string
            
            if player_name is None:  # Accounting for annotations
                player_name = rows[j].findAll('th')[0].contents[0].string
            
            player_url = rows[j].findAll('a',href=True)[0]['href']
            player_list.append({'name':player_name,
                                'url':player_url})
            
"""Scraping Player Data from created list"""

base_player_url = 'https://www.basketball-reference.com'
player_database = {}

for i in range(len(player_list)):
    full_player_url = f'{base_player_url}{player_list[i]["url"]}'
    player_name = player_list[i]['name']
    print(player_name)
    res = requests.get(full_player_url)
    html = res.content
    soup = bs4.BeautifulSoup(html, 'html.parser')
    
    """Per Game Stats"""
    player_pg_table = soup.find('div',attrs={'id':'all_per_game'}).contents[3]
    player_pg_stats = player_pg_table.findAll('tr')
    """Advanced Stats - Have to do a transform due to HTML"""
    player_adv_table = soup.find('div', attrs={'id':'all_advanced'}).contents[4]
    player_adv_stats = bs4.BeautifulSoup(player_adv_table, 'html.parser').findAll('tr')
    """Shooting Stats - Have to do a transform due to HTML"""
    player_sht_table = soup.find('div', attrs={'id':'all_shooting'}).contents[4]
    player_sht_stats = bs4.BeautifulSoup(player_sht_table, 'html.parser').findAll('tr')
    dnp_offset = 0  # Accounting for DNP seasons
    sht_offset = 0 # Accounting for years before shooting data
    adl_team_offset = 0  # Accounting for team on per game stats but not shot stats
    
    for j in range(1,len(player_pg_stats)):  # j is a season counter here
            pg_stats_table = player_pg_stats[j]
            adv_stats_table = player_adv_stats[j-dnp_offset]
            sht_stats_table = player_sht_stats[j + 1 - dnp_offset - sht_offset - adl_team_offset]  # Offset extra 1 for god knows why thanks HTML
            
            try:
                year = pg_stats_table['id'].split('.')[1] # Cutting year to last of 2 (eg, 2016-17 reports as 2017)
                if int(year) < 1997:
                    sht_offset+=1
    
            except KeyError:
                year = 'career'
                
            """Per Game Stats First"""
            stat_list = pg_stats_table.findAll('td')
            season_stats={}
            dnp_flag = False
            
            for k in range(len(stat_list)):
                try:
                    stat_name = stat_list[k]['data-stat']
                    stat_value = stat_list[k].string
                    season_stats[stat_name]=stat_value
                except KeyError:  # If data-stat isn't found it's due to a DNP season
                    season_stats = 'Did Not Play'
                    dnp_flag = True
                    
            if dnp_flag:  # If Seasons is DNP, increment offset and skip
                dnp_offset+=1
                continue
                
            """Adv Game Stats"""
            stat_list = adv_stats_table.findAll('td')
            
            for k in range(len(stat_list)):
                try:
                    stat_name = stat_list[k]['data-stat']
                    stat_value = stat_list[k].string
                    season_stats[stat_name]=stat_value
                except KeyError:
                    season_stats = 'Did Not Play'
            
            """Shooting Stats"""
            stat_list = sht_stats_table.findAll('td')
            
            for k in range(len(stat_list)):
                try: 
                    stat_name = stat_list[k]['data-stat']
                    if year!='career' and year < '1997':  
                        stat_value = None  # Want to keep rows
                    else:
                        stat_value = stat_list[k].string
                        
                    # In the situation, like Rasheed Wallace, where a player
                    # Has a team in their per game stats that doesn't appear
                    # On their shooting stats (<1997 only), then it adds
                    # An extra row which sends the shot list into an 
                    # Index Error. adl_team_offset accounts for that
                    
                    if stat_name == 'team_id' and stat_value != season_stats['team_id'] and year>'1996':
                        adl_team_offset+=1
                        
                    season_stats[stat_name]=stat_value
                except KeyError:
                    season_stats = 'Did Not Play'
                    
            if all(value is None for value in season_stats.values()): 
                continue   # Removing Dummy Rows
                
            if type(season_stats) is dict:
                season_stats.pop('DUMMY',None)  # Removing Dummy vals
                
            # IF is for adding Net New Players to database
            # ELIF is for adding players with more than 1 team in a season
            # Nested IF for adding 3rd or more team in a season
            # Nested ELSE for adding 2nd team in a season (converting to list)
            # Else for adding single season to existing player in database         
            
            if player_name not in player_database:
                    player_database[player_name]={year:season_stats}
            elif player_name in player_database and year in player_database[player_name]:
                if type(player_database[player_name][year]) is list:
                    player_database[player_name][year].append(season_stats)
                else:  
                    player_database[player_name][year]= [player_database[player_name][year], season_stats]
            else: 
                player_database[player_name][year]=season_stats
        

with open('sample.json', 'w') as outfile:  
    json.dump(player_database, outfile) 
            
            
            