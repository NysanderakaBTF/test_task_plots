import sqlite3
from datetime import datetime

import pandas as pd
from dash import html, Output, Input, dcc
from dash_extensions.enrich import (DashProxy,
                                    ServersideOutputTransform,
                                    MultiplexerTransform)
import dash_mantine_components as dmc
import plotly.express as px

CARD_STYLE = dict(withBorder=True,
                  shadow="sm",
                  radius="md",
                  style={'height': '450px'})


class EncostDash(DashProxy):
    def __init__(self, **kwargs):
        self.app_container = None
        super().__init__(transforms=[ServersideOutputTransform(),
                                     MultiplexerTransform()], **kwargs)


app = EncostDash(name=__name__)

conn = sqlite3.connect('../testDB.db')


def get_layout():
    return html.Div([
        dmc.Paper([
            dmc.Grid([
                dmc.Col([
                    dmc.Card(id='upper_left', children=[
                        dmc.Select(
                            label="Клиент",
                            placeholder="Select one",
                            id="client-select",
                            value="ng",
                            data=[
                                {"value": i, "label": i} for i in
                                pd.read_sql("SELECT DISTINCT client_name FROM sources",
                                            conn)['client_name']
                            ],
                            style={"width": 200, "marginBottom": 10},
                        ),
                        dmc.Select(
                            label="Точка учета",
                            placeholder="Select one",
                            id="endpoint-select",
                            value="ng",
                            data=[],
                            style={"width": 200, "marginBottom": 10},
                        ),
                        dmc.Select(
                            label="Сменный день",
                            placeholder="Select one",
                            id="shift-day-select",
                            value=None,
                            data=[],
                            style={"width": 200, "marginBottom": 10},
                        ),
                        html.Div(
                            id='shift_begin'
                        ),
                        html.Div(
                            id='shift_end'
                        ),

                        dmc.MultiSelect(
                            label="",
                            placeholder="",
                            id="filter-multi-select",
                            value=[],
                            data=[
                            ],
                            style={"width": 400, "marginBottom": 10},
                        ),
                        dmc.Button(
                            'Фильтровать',
                            id='filter'),
                        html.Div(
                            id='output')],
                             **CARD_STYLE)
                ], span=6),
                dmc.Col([
                    dmc.Card([
                        dcc.Graph(id='pie-chart')
                    ],
                        **CARD_STYLE)
                ], span=6),
                dmc.Col([
                    dmc.Card([
                        dcc.Graph(id='timeline')
                    ],
                        **CARD_STYLE)
                ], span=12),
            ], gutter="xl", )
        ])
    ])


app.layout = get_layout()


@app.callback(
    Output("timeline", "figure"),
    Output("filter", "n_clicks"),
    Input("client-select", "value"),
    Input("endpoint-select", "value"),
    Input("shift-day-select", "value"),
    Input("filter-multi-select", "value"),
    Input("filter", "n_clicks")

)
def build_timeline(client_select, endpoint_select, shift_day, filters, click):
    conn1 = sqlite3.connect('../testDB.db')
    if client_select != 'ng' and endpoint_select != 'ng' and shift_day != None:
        a = pd.read_sql(f"SELECT * "
                        f"FROM sources "
                        f"WHERE client_name like \'{client_select}\' "
                        f"and endpoint_name like \'{endpoint_select}\' "
                        f"and shift_day like \'{shift_day}\'", conn1)
        a['state_begin'] = pd.to_datetime(a['state_begin'])
        a['state_end'] = pd.to_datetime(a['state_end'])
        a['begin_dt'] = a.iloc[0]['state_begin'].strftime("%H:%M:%S (%d.%m)")
        a['duration'] = a['duration_hour']*60 + a['duration_min']
        a['duration'] = a['duration'].apply(lambda x: f"{x: .2f}")
        if filters and click > 0:
            a = a.loc[a['state'].isin(filters)]
        qq = px.timeline(a, x_start='state_begin', x_end='state_end', y='endpoint_name', color='color',
                         title="График состояний", custom_data=[a['state'],
                                                                a['reason'],
                                                                a['begin_dt'],
                                                                a['duration'],
                                                                a['shift_day'],
                                                                a['shift_name'],
                                                                a['operator']],
                         )
        qq.update_traces(showlegend=False,
                         hovertemplate=''
                                       'Состояние - <b> %{customdata[0]} </b> <br> '
                                       'Причина - <b> %{customdata[1]} </b> <br> '
                                       'Начало - <b> %{customdata[2]} </b> <br> '
                                       'Длительность - <b> %{customdata[3]} </b> мин. <br> '
                                       '<br>'
                                       'Сменный день - <b> %{customdata[4]} </b><br> '
                                       'Смена - <b>%{customdata[5]} </b><br> '
                                       'Оператор - <b>%{customdata[6]} </b> '
                                       '<extra></extra>'

                         )
        qq.update_xaxes(
            tickformat="%H",
            dtick=3600000
        )
        qq.update_yaxes(title="")
        qq.update_layout(title_x=0.5,
                         hoverlabel=dict(
                             bgcolor="white",
                         ),

                         )

        return [qq, 0]
    fig = px.pie([{'value': 0, 'name': 0}], values='value', names='name')
    fig.update_layout(showlegend=False)
    fig.update_xaxes(visible=False)
    fig.update_yaxes(visible=False)
    return [fig,0]


@app.callback(
    Output("shift_begin", "children"),
    Output("shift_end", "children"),
    Output("filter-multi-select", "data"),
    Input("client-select", "value"),
    Input("endpoint-select", "value"),
    Input("shift-day-select", "value")
)
def find_shift_begin_end(client, endpoint, shift_day):
    conn1 = sqlite3.connect('../testDB.db')
    if client != 'ng' and endpoint != 'ng' and shift_day != None:
        a = pd.read_sql(f"SELECT DISTINCT state_begin, state_end, state"
                        f" FROM sources"
                        f" WHERE client_name like \'{client}\'"
                        f"and endpoint_name like \'{endpoint}\'"
                        f"and shift_day like \'{shift_day}\' order by state_begin",
                        conn1)
        begin_dt = datetime.fromisoformat(a.iloc[0]['state_begin'])
        end_dt = datetime.fromisoformat(a.iloc[-1]['state_end'])
        return [["Начало периода " + begin_dt.strftime("%H:%M:%S (%d.%m)")],
                ["Конец периода " + end_dt.strftime("%H:%M:%S (%d.%m)")],
                a['state'].unique()]
    return [["Начало периода"], ["Конец периода"], []]


@app.callback(
    Output("shift-day-select", "data"),
    Input("client-select", "value"),
    Input("endpoint-select", "value"),
)
def set_days(value, endpoint):
    conn1 = sqlite3.connect('../testDB.db')
    if value != 'ng':
        a = pd.read_sql(f"SELECT DISTINCT shift_day FROM sources WHERE client_name like \'{value}\'"
                        f"and endpoint_name like \'{endpoint}\'",
                        conn1)['shift_day']
        return a
    return []


@app.callback(
    Output("endpoint-select", "data"),
    Input("client-select", "value"),
)
def set_days(client):
    conn1 = sqlite3.connect('../testDB.db')
    if client != 'ng':
        a = pd.read_sql(f"SELECT DISTINCT endpoint_name FROM sources WHERE client_name like \'{client}\'",
                        conn1)['endpoint_name']
        return a
    return []


@app.callback(
    Output('pie-chart', 'figure'),
    Input("client-select", "value"),
    Input("endpoint-select", "value"),
    Input("shift-day-select", "value")
)
def show_pie_chart(client, endpoint, shiftd):
    conn1 = sqlite3.connect('../testDB.db')
    if client != 'ng' and endpoint != 'ng' and shiftd != None:
        query1 = (f"SELECT * FROM sources WHERE client_name like \'{client}\'"
                  f" and endpoint_name like \'{endpoint}\' "
                  f" and shift_day like \'{shiftd}'")
        df2 = pd.read_sql(query1, conn1)
        df2['total_duration'] = df2['duration_hour'] + df2['duration_min'] / 60
        return px.pie(df2, values='total_duration', names='reason', color='color')
    else:
        fig = px.pie([{'value':0, 'name':0}], values='value', names='name')
        fig.update_layout(showlegend=False)
        fig.update_xaxes(visible=False)
        fig.update_yaxes(visible=False)
        return fig

if __name__ == '__main__':
    app.run_server(debug=True)
