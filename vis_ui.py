import streamlit as st
import streamlit.components.v1 as components

import pandas as pd
import matplotlib.pyplot as plt
import networkx as nx
from datetime import datetime
import numpy as np
from pyvis.network import Network
import pyvis

### Ways to filter the display of the graph
# Set FOCUS_MATCH to a single match name - shows competing teams and associated players for that match only
# Set TEAM_NODE_A and TEAM_NODE_B to two teams you want to see neighborhood connections of
#     Optionally cap the number of edges to show with MAX_EVENT_DISPLAY
# Set TIMESTAMP_START and TIMESTAMP_END to display all nodes and edges in a certain time window

# FOCUS_MATCH = 'ESPORTSTMNT01/1641087' # Match to focus on
# FOCUS_MATCH = None
MAX_EVENT_DISPLAY = 50 # custom number of neighbors to display; not impactful if FOCUS_MATCH set
# MAX_EVENT_DISPLAY = None
TEAM_NODE_A = 1740 # home team node to focus on and see neighbors of
TEAM_NODE_B = 1455 # away team node to focus on and see neighbors of
# Earliest timestamp: 2014-01-14 17:52:02
# Latest timestamp: 2023-11-20 20:40:26
# TIMESTAMP_START = np.datetime64('2023-11-20 19:59:21')
# TIMESTAMP_END = np.datetime64('2023-11-20 19:59:22')
TIMESTAMP_START = None
TIMESTAMP_END = None

### ----------------------------------------------------

df = pd.read_csv('data/processed/lol/events_with_gameid.csv')
dfLolTeams = pd.read_csv('data/processed/lol/teams_with_names.csv')
dfLolPlayers = pd.read_csv('data/processed/lol/players_with_names.csv')

df = pd.merge(df, dfLolTeams[['team_num', 'teamname']], how='left', left_on='u', right_on='team_num')
df = df.rename(columns={'teamname': 'u_name'})
df = df.drop('team_num', axis=1)
df_1 = df[df['v_type'] == 1]
df_2 = df[df['v_type'] == 2]

# Get team names in for v
df_1 = pd.merge(df_1, dfLolTeams[['team_num', 'teamname']], how='left', left_on='v', right_on='team_num')
df_1 = df_1.drop('team_num', axis=1)
df_1 = df_1.rename(columns={'teamname': 'v_name'})
# Get player names in for v
df_2 = pd.merge(df_2, dfLolPlayers[['player_num', 'playername']], how='left', left_on='v', right_on='player_num')
df_2 = df_2.drop('player_num', axis=1)
df_2 = df_2.rename(columns={'playername': 'v_name'})

df_recombined = pd.concat([df_1, df_2])
df = df_recombined.sort_values('e_idx')
df['ts'] = pd.to_datetime(df['ts'], unit='s')



def createGraph(teamA, teamB):
    print('=================CREATING GRAPH')
    focusNodes = [
        {
            'name': teamA,
            'nodeList': [],
            'edgeList': []
        },
        {
            'name': teamB,
            'nodeList': [],
            'edgeList': []
        }
    ]

    nodeLabelMapper = {
        1: '  Team:  \n',
        2: '  Player:  \n'
    }

    edgeLabelMapper = {
        1: 'Lost',
        2: 'Won',
        3: 'Joined',
        4: 'Info'
    }

    # Keys the same as node type
    # (1) team
    # (2) player
    nodeSizeMapper = {
        1: 30,
        2: 15
    }

    nodeColorMapper = {
        1: '#000099',
        2: '#0099FF'
    }

    # Keys the same as edge_type
    # (1) Lost
    # (2) Won
    # (3) Played
    # (4) Game info
    edgeColorMapper = {
        1: '#FF0000',
        2: '#15B01A',
        3: '#0099FF',
        4: '#C0C0C0'
    }

    edgeFontSizeMapper = {
        1: 24,
        2: 24,
        3: 12,
        4: 10
    }

    def edgeWeightMapper(type, size):
        if type == 1 or type == 2:
            return size * 3
        else:
            return 1 + (size % 10)

    def reformatLabel(text):
        return text.replace(' ', '\n')

    def fontAdjuster(type, text):
        if type == 1:
            return 24 if len(text) < 20 else 20
        else:
            return 18 if len(text) < 20 else 14

    for focusNode in focusNodes:
        if MAX_EVENT_DISPLAY:
            selectedTeam = df.loc[df['u'] == focusNode['name'], ['u', 'v', 'u_type', 'v_type', 'e_type', 'u_name', 'v_name', 'ts']].head(MAX_EVENT_DISPLAY)
        else:
            selectedTeam = df.loc[df['u'] == focusNode['name'], ['u', 'v', 'u_type', 'v_type', 'e_type', 'u_name', 'v_name', 'ts']]
        teamTypeDF = selectedTeam.drop_duplicates()
        us = list(teamTypeDF[['u', 'u_type', 'u_name', 'ts']].itertuples(index=False, name=None))
        vs = list(teamTypeDF[['v', 'v_type', 'v_name', 'ts']].itertuples(index=False, name=None))
        nodesList = list(list(dict.fromkeys(us + vs)))
        nodesList = list(map(lambda x: (x[0], {
            'type': x[1],
            'label': reformatLabel(x[2]),
            'title': 'TODO',
            'margin': 15,
            'color': {
                'background': nodeColorMapper[x[1]], 
                'highlight': {
                    'background': nodeColorMapper[x[1]],
                    'border': 'magenta'
                },
                'hover': {
                    'border': 'gray'
                }
            },
            # 'physics': False,
            # 'mass': 8 if x[1] == 1 else 2,
            'mass': 5,
            'shape': 'circle',
            'font': {'size': fontAdjuster(x[1], x[2]), 'color': 'white'},
            'borderWidthSelected': 6
            }), nodesList))
        edgesWithDups = selectedTeam.groupby(selectedTeam.columns.tolist(), as_index=False).size()
        edgesWithDupsList = list(edgesWithDups[['u', 'v', 'e_type', 'size', 'ts']].itertuples(index=False, name=None))
        # Change arrow display direction if edge type is 3 (to show player joining team):
        edgesWithDupsList = list(map(lambda x: (x[1] if x[2] == 3 else x[0], x[0] if x[2] == 3 else x[1], { 
            'edge_type': x[2], 
            'weight': edgeWeightMapper(x[2], x[3]),
            'label': edgeLabelMapper[x[2]],
            'title': str(pd.to_datetime(str(x[4])).strftime('%h %d %Y %H:%M:%S')),
            'color': edgeColorMapper[x[2]],
            'font': {'size': edgeFontSizeMapper[x[2]]},
            'smooth': True,
            # 'arrowSize': 5,
            # 'physics': False
            }), edgesWithDupsList))
        focusNode['nodeList'] = nodesList
        focusNode['edgeList'] = edgesWithDupsList

        focusGraph = nx.MultiDiGraph()

        lineWidthMapper = {
            1: 6,
            2: 6,
            3: 3,
            4: 1
        }

        arrowSizeMapper = {
            1: 10,
            2: 40,
            3: 12,
            4: 1
        }

        allNodesList = focusNodes[0]['nodeList'] + focusNodes[1]['nodeList']
        allEdgesList = focusNodes[0]['edgeList'] + focusNodes[1]['edgeList']

        focusGraph.add_nodes_from(allNodesList)
        focusGraph.add_edges_from(allEdgesList)

        options = {
            'arrowstyle': '->',
            'arrowsize': list(arrowSizeMapper[edge_type] for u, v, edge_type in list(focusGraph.edges(data='edge_type')))
        }


        net = Network(
            '1500px', '1500px',
            directed=True,
            # heading='League of Legends',
            # select_menu=True,
            # filter_menu=True,
            # bgcolor='#222222',
            # font_color='white'
        )
        net.from_nx(focusGraph) # Create directly from nx graph

        options = {
            # 'physics':{ # physics very distracting with large/non-capped number of edges, even with just 2 teams
            #     'barnesHut':{
            #         'gravitationalConstant':-15000, # seemingly best around -15000
            #         'centralGravity': 5, # seemingly best at 5
            #         'springLength': 200,
            #         'springConstant': 0.7,
            #         'damping': 3,
            #         'avoidOverlap': 0 # higher vals push nodes away from each other actively
            #     }
            # },
            'interaction':{   
                'selectConnectedEdges': True,
                'hover': True
            },
            'edges': {
                'arrowStrikethrough': False
            }
        }

        net.options=options

        # net.show('test1.html', notebook=False, ) # do NOT remove the notebook=False

###-------------------------------------------------------------------------------

styl = f"""
    <style>
        .st-emotion-cache-1y4p8pa{{
            max-width: none !important;
        }}
        .card{{
            border: none !important;
        }}
    </style>
    """
st.markdown(styl, unsafe_allow_html=True)
st.title('League of Legends')
st.sidebar.title('Choose a focus method:')
useDemo = st.sidebar.button('Use Demo Teams')
mainOption = st.sidebar.selectbox('Select one:', ('With 2 teams', 'Time window', 'By match', 'Node adjacency'))

if useDemo:
    st.sidebar.text('Demo Teams:\nNongshim RedForce Academy (Home)\nDRX Academy (Away)')
    teamAOption = 'Fnatic --- Team: 827'
    teamBOption = 'Gambit Gaming --- Team: 391'

# chosenTeamMatch = ''
# chosenTeamMatch = st.sidebar.empty()

if mainOption == 'With 2 teams':
    with st.sidebar.form(key='my_form'):
        dfLolTeams = pd.read_csv('data/processed/lol/teams_with_names.csv')
        dfLolTeams = dfLolTeams.sort_values('teamname')
        dfLolTeams['displayname'] = dfLolTeams['teamname'] + ' --- Team: ' + dfLolTeams['team_num'].astype(str)
        listLolTeams = dfLolTeams['displayname'].tolist()

        # st.empty() workaround for updating fields before submitting
        placeholder_Team_A_component = st.empty()
        placeholder_Team_A_react = st.empty()
        placeholder_Team_B_component = st.empty()
        placeholder_Team_B_react = st.empty()
        placeholder_toggle = st.empty()
        placeholder_toggle_react = st.empty()
        placeholder_match_component = st.empty()
        placeholder_match_react = st.empty()

        teamAOption=''
        teamBOption=''
        chosenTeamMatch=''
        listChosenTeamMatches = ['No selection']
        
        submit_button = st.form_submit_button(label='Submit')

    with placeholder_Team_A_component:
        teamAOption = st.selectbox('Team A:', listLolTeams, key='teamA')

    with placeholder_Team_A_react:
        print('Team A selected')

    with placeholder_Team_B_component:
        teamBOption = st.selectbox('Team B:', listLolTeams, key='teamB')

    with placeholder_Team_B_react:
        print('Team B selected')

    with placeholder_match_component:
        print('placeholder_match_component')
        truncTeamA = int(teamAOption.split(' --- Team: ')[1])
        truncTeamB = int(teamBOption.split(' --- Team: ')[1])
        print('team A: ' + str(truncTeamA))
        print('team B: ' + str(truncTeamB))
        teams_df = df.loc[(df['u'] == truncTeamA) | (df['v'] == truncTeamB)]
        dfGames = df.loc[(df['u'].isin([truncTeamA, truncTeamB])) & (df['v'].isin([truncTeamA, truncTeamB])) & (df['e_type'].isin([1, 2]))] # should be sorted by date
        listGames = list(dfGames[['u', 'v', 'ts', 'gameid']].itertuples(index=False))
        listChosenTeamMatches = ['No selection']
        for game in listGames:
            listChosenTeamMatches.append(game[3] + ' : ' + str(game[2]) + ' : ' + str(game[0]) + ' (H) vs ' + str(game[1]) + ' (A)')
        chosenTeamMatch = st.selectbox('(Optional) Choose a match between those teams:', options=listChosenTeamMatches, key='chosenTeamMatch')

    with placeholder_match_react:
        print('Chosen teams match')
        if chosenTeamMatch == 'No selection':
            print('No selection')

    # TODO: Time window
    # Print earliest and latest timestamps for teams A and B
                
    # Enable to display a single match
    # if chosenTeamMatch:
    #     print('INSIDE NO MATCH')
    #     df = df.loc[(df['gameid'] == chosenTeamMatch.split(': ')[0])]
    #     print(df)

    #     # Time window selection
    #     # if TIMESTAMP_START and TIMESTAMP_END:
    #     #     df = df.loc[(df['ts'] >= TIMESTAMP_START) & (df['ts'] <= TIMESTAMP_END)]
    #     #     print('SELECTING TIME WINDOW BETWEEN ' + str(TIMESTAMP_START) + ' AND ' + str(TIMESTAMP_END))
            
    with st.sidebar:
        if submit_button:
            print('--------------USER SUBMITTED 2 TEAMS FORM--------------')
            print(teamAOption)
            print(teamBOption)
            print(chosenTeamMatch)
        #     createGraph(teamAOption, teamBOption)

    if mainOption == 'Time window':
        print('Time window!')
        



    # HtmlFile = open('test1.html', 'r', encoding='utf-8')
    # source_code = HtmlFile.read() 
    # components.html(source_code, height=1600, width=1502)
