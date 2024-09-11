import streamlit as st
import folium
from streamlit_folium import st_folium

import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import os

# Load the CSV files from the current directory
csv_directory = '.'  # Current directory
csv_files = [f for f in os.listdir(csv_directory) if f.endswith('.csv')]
csv_files = sorted(csv_files, reverse=True)

# Ensure there's at least one CSV file
if not csv_files:
    st.error("No CSV files found in the directory.")
else:
    # Initialize session state variables if they don't exist
    if 'selected_file' not in st.session_state:
        st.session_state.selected_file = csv_files[1] #2022
        st.session_state.year = st.session_state.selected_file.split('.')[0].split('_')[-1]
    if 'selected_country' not in st.session_state:
        st.session_state.selected_country = None
    if 'selected_sector' not in st.session_state:
        st.session_state.selected_sector = None

    # File selection dropdown
    selected_file = st.selectbox("Select a CSV file", options=csv_files, index=csv_files.index(st.session_state.selected_file))

    # If a new file is selected, update the session state and reset selections
    if selected_file != st.session_state.selected_file:
        st.session_state.selected_file = selected_file
        st.session_state.year = selected_file.split('.')[0].split('_')[-1]
        st.session_state.selected_country = None
        st.session_state.selected_sector = None
        st.rerun()

    # Load the DataFrame
    # df = pd.read_csv(os.path.join(csv_directory, selected_file))
    # df = pd.read_csv('ct_treemap_data.csv')

    def load_data(file_path):
        df = pd.read_csv(file_path)
        return df

    df = load_data(os.path.join(csv_directory, selected_file))

    # Formatting function for generating a treemap figure
    def generate_fig(data, path, value, color):
        total_value = data['co2e_100yr'].sum()

        fig = px.treemap(data, path=path, values=value, color=color,
                         title='Treemap for Climate TRACE data')

        fig.update_layout(
            width=700,
            height=300,
            margin=dict(t=0, l=0, b=0, r=0),  # Remove margins around the treemap
            paper_bgcolor='white',  # Background color of the paper
            uniformtext_minsize=10,  # Minimum text size for labels
            uniformtext_mode='hide',  # Hide text if it doesn't fit
            clickmode='event+select',
            annotations=[
                go.layout.Annotation(
                    text=f"Total CO2e (100 yr): {total_value:,}",
                    showarrow=False,
                    xref="paper",
                    yref="paper",
                    x=0.5,
                    y=1.005,
                    font=dict(size=14, color="black"),
                    align="center"
                )
            ]
        )
        fig.update_traces(
            hovertemplate='%{label}<br>Value: %{value}<br>Percent of Total: %{percent.entry:.2%}',
            textinfo='label+percent entry+value',
            textfont_size=10,
            marker=dict(
                line=dict(width=0)  # Reduce outline width
            )
        )

        return fig

    # Setup streamlit layouts
    layout_col1, layout_col2 = st.columns(2)  # Create two columns

    with layout_col1:
        # Section 1: Treemap by Sector
        st.header("Climate TRACE " + st.session_state.year)
        fig_all = generate_fig(df, ['sector','subsector'], 'co2e_100yr', None)
        st.plotly_chart(fig_all, use_container_width=True)

        # Section 2: Treemap by Sector/Country
        st.header("Climate TRACE Sector " + st.session_state.year)
        sector_list = df['sector'].unique()
        selected_sector = st.selectbox("Select a Sector", options=sorted(sector_list))

        if selected_sector != st.session_state.selected_sector:
            st.session_state.selected_sector = selected_sector

        filtered_df_sector = df[df['sector'] == selected_sector]
        fig_sector = generate_fig(filtered_df_sector, ['subsector','iso3_country'], 'co2e_100yr', 'continent_ct')
        st.plotly_chart(fig_sector, use_container_width=True)

    with layout_col2:
        # Set up the title of the Streamlit app
        st.header("Climate TRACE Asset")
        map_center = [37.7749, -122.4194]  # Example coordinates (San Francisco)
        folium_map = folium.Map(location=map_center, zoom_start=12)

        folium.Marker(
            location=[37.7749, -122.4194], 
            popup='San Francisco', 
            icon=folium.Icon(color='blue')
        ).add_to(folium_map)

        st_folium(folium_map, width=700, height=300)

        # Section 3: Treemap by Country/Sector
        st.header("Climate TRACE Country " + st.session_state.year)
        country_list = df['iso3_country'].unique()
        # selected_country = st.selectbox("Select a Country", options=country_list, index=0 if st.session_state.selected_country is None else country_list.tolist().index(st.session_state.selected_country))
        selected_country = st.selectbox("Select a Country", options=sorted(country_list))

        if selected_country != st.session_state.selected_country:
            st.session_state.selected_country = selected_country

        filtered_df_country = df[df['iso3_country'] == selected_country]
        fig_country = generate_fig(filtered_df_country, ['sector','subsector'], 'co2e_100yr', None)
        st.plotly_chart(fig_country, use_container_width=True)