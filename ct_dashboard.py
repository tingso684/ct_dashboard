import streamlit as st
from streamlit_folium import st_folium
from st_aggrid import AgGrid, GridOptionsBuilder, JsCode, GridUpdateMode
import folium
from folium import Popup, Marker, GeoJson
import requests
import matplotlib.colors as mcolors
import matplotlib.cm as cm
from matplotlib.colors import Normalize
from branca.colormap import linear
from shapely.geometry import shape
from shapely.ops import transform
from shapely import wkt, wkb
import pyproj
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import geopandas as gpd
import os
import re
import json
from datetime import datetime
import numpy as np
from climate_trace_tools.compare.aggregate_up.aggregate_up_plotting import CountryPlotting


# Load the CSV files from the current directory
csv_directory = './data'  # Current directory
csv_files = [f for f in os.listdir(csv_directory) if f.endswith('.csv') and 'ct_assets_' in f]
csv_files = sorted(csv_files, reverse=True)

file_prefix_top500 = 'asset/ct_assets_top500_'
file_prefix_asset = 'asset/ct_assets_assets_trim_'
file_prefix = 'ct_assets_slim_'
list_files = [re.search(r"\['(.*?)'\]_(\d{8})", f) for f in csv_files]

gas_type0 = ['co2e_100yr', 'co2', 'ch4', 'n2o', 'pm2_5','so2','nox','co','nh3','nmvoc','bc','oc']
gas_type = sorted(list(set([v.group(1) for v in list_files])), reverse=False)
gas_type = [x for x in gas_type0 if x in gas_type]

dt_str = sorted(list(set([v.group(2) for v in list_files])), reverse=True)

with open(csv_directory + '/ct_color.json', 'r') as json_file:
    ct_color = json.load(json_file)

all_years = []

# Basic setup
st_layout = {'width_col': 1000,
             'height_row':  500}

st.set_page_config(layout="wide")

st.markdown("""         
    <style>
    /* Set background color for the entire app
    .stApp {
        background-color: #EBE6E6;  /* You can replace #F5F5F5 with any color code */
    }*/
                            
    /* Map container custom styling */    
    .map-container {
        width: 100%;  /* Make the map container full width */
        height: 100%; /* Set a fixed height for the map */
        background-color: #EBE6E6;
    }
    </style>
""", unsafe_allow_html=True)

trigger_bar_total = True

def short_scale_formatter(value):
                    if value >= 1_000_000_000:
                        return f"{value / 1_000_000_000:,.1f}G"
                    if value >= 1_000_000:
                        return f"{value / 1_000_000:,.1f}M"
                    elif value >= 1_000:
                        return f"{value / 1_000:,.0f}K"
                    else:
                        return f"{value:.0f}"


# Ensure there's at least one CSV file
if not csv_files:
    st.error("No CSV files found in the directory.")
else:
    layout_tab1, layout_tab2 = st.tabs(["**Climate TRACE Dashboard**", "**Inventory Comparison**"])

    with layout_tab1:

        # Initialize session state variables if they don't exist
        if 'file' not in st.session_state:
            st.session_state.snapshot = dt_str[0]
            st.session_state.gas = gas_type[0]

            try:
                fname = file_prefix + "['" + st.session_state.gas + "']" + "_" + st.session_state.snapshot + '.csv'
                st.session_state.file = fname 
                st.session_state.df = pd.read_csv(os.path.join(csv_directory, st.session_state.file))

                fname = file_prefix_asset + "['" + st.session_state.gas + "']" + "_" + st.session_state.snapshot + '.csv'
                st.session_state.file_asset = fname 
                st.session_state.df_asset = pd.read_csv(os.path.join(csv_directory, st.session_state.file_asset))

                fname = file_prefix_top500 + "['" + st.session_state.gas + "']" + "_" + st.session_state.snapshot + '.csv'
                st.session_state.file_top500 = fname 
                st.session_state.df_top500 = pd.read_csv(os.path.join(csv_directory, st.session_state.file_top500))
            except:
                trigger = False

        if 'choice' not in st.session_state:
            st.session_state.choice = 'all sectors (include forestry)' # or 'ex-forestry'

        if 'year' not in st.session_state:
            all_years = sorted(st.session_state.df.year.unique().tolist(), reverse=True)
            st.session_state.year0 = all_years[-1]
            st.session_state.year = all_years[1]
            st.session_state.year1 = all_years[2]
            st.session_state.df_yr = st.session_state.df.loc[st.session_state.df['year']==int(st.session_state.year),:]

        if 'country' not in st.session_state:
            st.session_state.country = "global"
            st.session_state.country_full = "global"

        if 'sector' not in st.session_state:
            st.session_state.sector = "all sectors"

        if 'subsector' not in st.session_state:
            st.session_state.subsector = "all subsectors"

        if 'sector1' not in st.session_state:
            st.session_state.sector1 = "all sectors"

        if 'subsector1' not in st.session_state:
            st.session_state.subsector1 = "all subsectors"

        if 'sector2' not in st.session_state:
            st.session_state.sector2 = "all sectors"

        if 'subsector2' not in st.session_state:
            st.session_state.subsector2 = "all subsectors"

        if 'topAsset' not in st.session_state:
            st.session_state.topAsset = "global"

        if 'topAssetField' not in st.session_state:
            st.session_state.topAssetField = "emissions_quantity"

        if 'topRank' not in st.session_state:
            st.session_state.topRank = 5

        if 'rankYear' not in st.session_state:
            st.session_state.rankYear = st.session_state.year

        if 'country_comp' not in st.session_state:
            st.session_state.country_comp = "USA"

        if 'year_comp' not in st.session_state:
            st.session_state.year_comp = st.session_state.year

        if 'gas_comp' not in st.session_state:
            st.session_state.gas_comp = st.session_state.gas

        if 'chart_comp_loaded' not in st.session_state:
            st.session_state.chart_comp_loaded = False
            st.session_state.cp = None

        # File selection dropdown
        st.write("**Climate TRACE 2024 v4 release includes 68 sectors covering over 660 miliions assets globally**")
        # st.write("**Data:  v4_2024 (20241027),  v3_2023 (20240918)**")
        st.write("*This web tool is for the internal use of Climate TRACE and its partners only.  The data available here may be revised, updated, rearranged, or deleted without prior information to users and is not warranted to be error-free.*")
        with st.container():
            layout_col1, layout_col2 = st.columns(2)
            with layout_col1:
                selected_snapshot = st.selectbox("Select data: [v4 - 20241027 | v3 - 20240918]", options=dt_str, index=0)

            with layout_col2:
                selected_gas = st.selectbox("Select a gas", options=gas_type, index=0)

        if selected_snapshot != st.session_state.snapshot:
            st.session_state.snapshot = selected_snapshot

        if selected_gas != st.session_state.gas:
            st.session_state.gas = selected_gas

        selected_file = file_prefix + "['" + st.session_state.gas + "']" + "_" + st.session_state.snapshot + '.csv'
        trigger = selected_file in csv_files

        if trigger == False:
            st.write('File is not available for the snapshot date and gas. Please select other')
        else:
            if selected_file != st.session_state.file:
                st.session_state.file = selected_file

                st.session_state.df = pd.read_csv(os.path.join(csv_directory, st.session_state.file))
                st.session_state.df_yr = st.session_state.df.loc[st.session_state.df['year']==int(st.session_state.year),:]

                if st.session_state.choice == 'ex-forestry':
                    st.session_state.df = st.session_state.df.loc[st.session_state.df['sector'].isin(['forestry-and-land-use'])==False,:]
                    st.session_state.df_yr = st.session_state.df.loc[st.session_state.df['year']==int(st.session_state.year),:]

            selected_file_asset = file_prefix_asset + "['" + st.session_state.gas + "']" + "_" + st.session_state.snapshot + '.csv'
            if selected_file_asset != st.session_state.file_asset:
                st.session_state.file_asset = selected_file_asset 
                st.session_state.df_asset = pd.read_csv(os.path.join(csv_directory, st.session_state.file_asset))

                if st.session_state.choice == 'ex-forestry':
                    st.session_state.df_asset = st.session_state.df_asset.loc[st.session_state.df_asset['sector'].isin(['forestry-and-land-use'])==False,:]

            selected_file_top500 = file_prefix_top500 + "['" + st.session_state.gas + "']" + "_" + st.session_state.snapshot + '.csv'
            if selected_file_asset != st.session_state.file_top500:
                st.session_state.file_top500 = selected_file_top500 
                st.session_state.df_top500 = pd.read_csv(os.path.join(csv_directory, st.session_state.file_top500))

                if st.session_state.choice == 'ex-forestry':
                    st.session_state.df_top500 = st.session_state.df_top500.loc[st.session_state.df_top500['sector'].isin(['forestry-and-land-use'])==False,:]

            # Year selection dropdown
            with st.container():
                layout_col1, layout_col2, layout_col3 = st.columns(3)  # Create two columns

                all_years = sorted(st.session_state.df.year.unique().tolist(), reverse=True)
                    
                with layout_col1:
                    selected_choice = st.selectbox("Select data type", options=['all sectors (include forestry)', 'ex-forestry'], index=1)

                if selected_choice != st.session_state.choice:
                    st.session_state.choice = selected_choice

                    if st.session_state.choice == 'ex-forestry':
                        st.session_state.df = st.session_state.df.loc[st.session_state.df['sector'].isin(['forestry-and-land-use'])==False,:]
                        st.session_state.df_yr = st.session_state.df.loc[st.session_state.df['year']==int(st.session_state.year),:]
                        st.session_state.df_asset = st.session_state.df_asset.loc[st.session_state.df_asset['sector'].isin(['forestry-and-land-use'])==False,:]
                        st.session_state.df_top500 = st.session_state.df_top500.loc[st.session_state.df_top500['sector'].isin(['forestry-and-land-use'])==False,:]

                    else:
                        st.session_state.df = pd.read_csv(os.path.join(csv_directory, st.session_state.file))
                        st.session_state.df_yr = st.session_state.df.loc[st.session_state.df['year']==int(st.session_state.year),:]
                        st.session_state.df_asset = pd.read_csv(os.path.join(csv_directory, st.session_state.file_asset))
                        st.session_state.df_top500 = pd.read_csv(os.path.join(csv_directory, st.session_state.file_top500))


                with layout_col2:
                    selected_year = st.selectbox("Select current year", options=all_years, index=1)

                if selected_year != st.session_state.year:
                    st.session_state.year = selected_year
                    st.session_state.df_yr = st.session_state.df.loc[st.session_state.df['year']==int(st.session_state.year),:]
                    # st.session_state.df_exf_yr = st.session_state.df_exf.loc[st.session_state.df_exf['year']==int(st.session_state.year),:]

                    # st.rerun()

                with layout_col3:
                    selected_year_comp = st.selectbox("Select previous year", options=all_years, index=2)

                if selected_year_comp != st.session_state.year1:
                    st.session_state.year1 = selected_year_comp


            # Formatting function for generating a treemap figure
            def generate_fig(data, path, value, color):
                total_value = int(data[value].sum())

                fig = px.treemap(data, path=path, values=value, color=color, color_discrete_map=ct_color, maxdepth=2,
                                title='Treemap for Climate TRACE data')

                fig.update_layout(
                    width=st_layout['width_col'],
                    height=st_layout['height_row'],
                    margin=dict(t=0, l=0, b=0, r=0),  # Remove margins around the treemap
                    paper_bgcolor='white',  # Background color of the paper
                    plot_bgcolor='white',
                    uniformtext_minsize=10,  # Minimum text size for labels
                    uniformtext_mode='hide',  # Hide text if it doesn't fit
                    clickmode='event+select',
                    annotations=[
                        go.layout.Annotation(
                            text=f"Total Emissions (ex-Forestry): {total_value:,}",
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
                    hovertemplate='%{label}<br>Value: %{value:,.0f}<br>Percent of Total: %{percentRoot:.1%}',
                    textinfo='label+percent entry+value',
                    textfont_size=10,
                    marker=dict(
                        line=dict(width=0.5)  # Reduce outline width
                    ),
                )

                return fig

            st.markdown("---")
            # Layout:  First Row
            with st.container():
                layout_col1, layout_col2 = st.columns(2)  # Create two columns

                with layout_col1:
                    st.header("Global Emissions")
                    st.write(f"From {st.session_state.year0} to {st.session_state.year}")

                    filtered_df_sec = st.session_state.df.loc[st.session_state.df['year']<=st.session_state.year,:].groupby(['year','sector']).emissions_quantity.sum().reset_index()
                    fig_all_sec_bar = px.bar(
                                filtered_df_sec, 
                                x='year', 
                                y='emissions_quantity', 
                                color='sector',  # This will create the stack
                                color_discrete_map=ct_color
                                )

                    # Always trigger_bar_total = True
                    fig_all_sec_bar.update_traces(textposition='inside', textfont_size=10, texttemplate='%{y:.2s}', hovertemplate='Sector: %{x}<br>Emissions: %{y:.2s}')
                    # fig_all_sec_bar.update_layout(plot_bgcolor='#EBE6E6', paper_bgcolor='#EBE6E6')
                    
                    for year, year_data in filtered_df_sec.groupby('year'):
                        total_value = year_data['emissions_quantity'].sum()
                        top_of_bar = year_data.loc[year_data['emissions_quantity'] > 0, 'emissions_quantity'].sum()

                        fig_all_sec_bar.add_annotation(
                            x=year,
                            y=top_of_bar,
                            text=short_scale_formatter(total_value),  # Total value on top of the bar
                            showarrow=False,
                            font=dict(size=10),
                            yshift=10,  # Adjust the vertical position
                            xanchor='center'
                        )

                    st.plotly_chart(fig_all_sec_bar)

                with layout_col2:
                    # Set up the title of the Streamlit app
                    st.header("Country Hotspot")
                    # st.write(f"current year [{st.session_state.year}] - previous year [{st.session_state.year1}]")

                    # *** Setup sector and subsector selection here ***
                    layout_col2a, layout_col2b = st.columns(2)  # Create two columns

                    with layout_col2a:
                        sector_list = ['all sectors'] + sorted(st.session_state.df_yr['sector'].unique().tolist())
                        selected_sector1 = st.selectbox("Select a Sector", options=sector_list, index=0, key='sector_hotspot')

                    if selected_sector1 != st.session_state.sector1:
                        st.session_state.sector1 = selected_sector1

                    with layout_col2b:
                        subsector_list = ['all subsectors'] + sorted(st.session_state.df_yr.loc[st.session_state.df_yr['sector']==st.session_state.sector1,'subsector'].unique().tolist())
                        selected_subsector1 = st.selectbox("Select a Subsector", options=subsector_list, index=0, key='subsector_hotspot')

                    if selected_subsector1 != st.session_state.subsector1:
                        st.session_state.subsector1 = selected_subsector1

                    if st.session_state.subsector1 == 'all subsectors':
                        filtered_df_sector_hotspot = st.session_state.df[st.session_state.df['sector'] == st.session_state.sector1] if st.session_state.sector1 != 'all sectors' else st.session_state.df
                    else:
                        filtered_df_sector_hotspot = st.session_state.df[st.session_state.df['subsector'] == st.session_state.subsector1]
                    
                    gradient_bar_html = """
                    <div style="
                        width: 200px; height: 20px;
                        background: linear-gradient(to right, #CC3333, white, #228B22);
                        font-size:12px;
                    ">
                        <div style="text-align:center;">
                            Worse &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; Better
                        </div>
                    </div>
                    """
                    st.markdown(f"""
                        <div style="display: flex; align-items: center; justify-content: space-between;">
                            <div>current year [{st.session_state.year}] - previous year [{st.session_state.year1}]</div> 
                            <div>{gradient_bar_html}</div>
                        </div>
                    """, unsafe_allow_html=True)

                    df_tb = filtered_df_sector_hotspot[['year','iso3_country','country','sector','subsector','asset_type','emissions_quantity','activity','emissions_factor']] 
                    df_tb = df_tb.loc[df_tb['year'].isin([st.session_state.year,st.session_state.year1]),:]
                    df_tb.rename(columns={'emissions_quantity': 'emissions'}, inplace=True)
                    df_tb = df_tb.pivot_table(index=['iso3_country','country'], columns='year', values='emissions', aggfunc='sum')
                    df_tb = df_tb.dropna(how='any', axis=0)
                    df_tb = df_tb.loc[(df_tb != 0).any(axis=1), (df_tb != 0).any(axis=0)].reset_index()

                    fds_diff = 'emissions_' + '-'.join([str(st.session_state.year), str(st.session_state.year1)])
                    df_tb[fds_diff] = df_tb[st.session_state.year] - df_tb[st.session_state.year1]

                    #Coloring
                    custom_percentiles = [0, 0.001, 0.02, 0.1, 0.15, 0.5, 0.85, 0.95, 0.99, 0.999, 1.0] 

                    # bins = pd.qcut(df_tb[fds_diff], q=10)
                    bins = pd.qcut(df_tb[fds_diff], q=custom_percentiles, duplicates='drop')

                    # Normalize for colormap to control darkness
                    scalar = 0.5
                    norm_positive = Normalize(vmin=0, vmax=df_tb[fds_diff].max()*scalar)  # Normalize for positive values
                    norm_negative = Normalize(vmin=df_tb[fds_diff].min()*scalar, vmax=0)  # Normalize for negative values

                    # Create colormaps with normalization: 'Greens' reversed for negative, 'Reds' for positive
                    cmap_red = cm.ScalarMappable(norm=norm_positive, cmap='Reds').cmap
                    cmap_green = cm.ScalarMappable(norm=norm_negative, cmap='Greens_r').cmap  # '_r' reverses the colormap

                    # Create a dictionary to map bins to colors for negative and positive values
                    bin_colors = {}
                    for i, category in enumerate(bins.cat.categories):
                        if category.right > 0:  # Positive bins
                            normalized_value = norm_positive(category.right)  # Normalize positive values
                            bin_colors[category] = mcolors.rgb2hex(cmap_red(normalized_value))
                        else:  # Negative bins
                            normalized_value = norm_negative(category.left)  # Normalize negative values
                            bin_colors[category] = mcolors.rgb2hex(cmap_green(normalized_value))

                    df_tb['Color'] = bins.map(bin_colors)

                    #Sizing
                    custom_percentiles = [0, 0.3, 0.5, 0.7, 0.75, 0.8, 0.85, 0.9, 0.95, 0.99, 1.0] 
                    # size_bins = pd.qcut(df_tb[st.session_state.year], q=custom_percentiles, labels=range(5, 15), duplicates='drop')
                    size_bins = pd.qcut(df_tb[st.session_state.year], q=custom_percentiles, duplicates='drop')
                    labels = range(15 - size_bins.nunique(), 15)
                    size_bins = pd.qcut(df_tb[st.session_state.year], q=custom_percentiles, labels=labels, duplicates='drop')
                    df_tb['Size'] = size_bins

                    #Plot
                    # Load internal GADM boundary CSV into a DataFrame
                    df_gadm = pd.read_csv(os.path.join(csv_directory, 'ct_gadm_cty_point_20240915.csv'))
                    df_gadm['geometry'] = df_gadm['geometry'].apply(wkt.loads)
                    gdf_gadm = gpd.GeoDataFrame(df_gadm, geometry='geometry')

                    gdf_gadm = gdf_gadm.merge(df_tb, on=['iso3_country'], how='inner')
                    # st.write(df_tb)

                    map_center = [0, 0]  # Default center
                    folium_map = folium.Map(location=map_center, zoom_start=2)

                    # Function to add markers to the map
                    for idx, row in gdf_gadm.iterrows():
                        coords = (row['geometry'].y, row['geometry'].x)
                        color = row['Color'] if pd.notna(row['Color']) else 'lightgray'
                        size = float(row['Size']) if pd.notna(row['Size']) else 5.0  # Allow decimal size

                        folium.CircleMarker(
                            location=coords,
                            radius=size,
                            color=color,
                            fill=True,
                            fill_color=color,
                            fill_opacity=1,
                            popup = f"{row['country']} ({row['iso3_country']}) <br><br>Emissions: {row[st.session_state.year]:,.0f}, Change: {row[f'{fds_diff}']:,.0f}"
                        ).add_to(folium_map)

                    st_folium(folium_map, width=st_layout['width_col'], height=st_layout['height_row']-20)

            with st.expander("**Expand to view Global emissions details**", expanded=False):
                with st.container():
                    st.header(f"Global emissions")
                
                    df_global_sec = st.session_state.df.groupby(['year','sector'])['emissions_quantity'].sum().reset_index()
                    df_global_all = st.session_state.df.groupby(['year'])['emissions_quantity'].sum().reset_index()
                    df_global_all['sector'] = 'all sectors'
                    
                    df_global = pd.concat([df_global_all, df_global_sec], ignore_index=True).set_index(['sector'])

                    df_global = df_global.pivot_table(index=['sector'], columns='year',values='emissions_quantity', aggfunc='sum')
                    df_global = df_global.sort_values(by='sector', key=lambda x: x == 'all sectors', ascending=False)
                    df_global = df_global[[x for x in df_global.columns if x <= st.session_state.year]]

                    st.dataframe(df_global.round(0), use_container_width=True, height=st_layout['height_row']-80)

                with st.container():
                    st.header(f"Global emissions change (in metric tons)")

                    df_global_diff = df_global.diff(axis=1)

                    st.dataframe(df_global_diff.round(0), use_container_width=True, height=st_layout['height_row']-80)

                with st.container():
                    st.header(f"Global emissions change (YoY %)")

                    # df_global_pct = df_global_diff/df_global.bfill(axis=1) -1
                    df_shifted = pd.DataFrame(np.nan, index=df_global.index, columns=df_global.columns)  # Create a new DataFrame filled with NaN
                    df_shifted.iloc[:, 1:] = df_global.iloc[:, :-1]  # Copy the values from the original DataFrame shifted to the right

                    df_global_pct = df_global_diff/df_shifted
                    df_global_pct = df_global_pct.applymap(lambda x: "{:,.2f}%".format(x*100) if pd.notna(x) else x)

                    st.dataframe(df_global_pct, use_container_width=True, height=st_layout['height_row']-80)
                
            with st.container():        
                layout_col1, layout_col2 = st.columns(2)  # Create two columns
                    
                with layout_col1:
                    # Section 3: Treemap by Country/Sector
                    st.header("Country Emissions")

                    country_list = ['global'] + sorted(st.session_state.df_yr['country'].unique().tolist())
                    selected_country = st.selectbox("Select a Country", options=country_list)
                    if selected_country != 'global':
                        selected_country = st.session_state.df_yr.loc[st.session_state.df_yr['country']==selected_country,'iso3_country'].values[0]

                    if selected_country != st.session_state.country:
                        st.session_state.country = selected_country
                        st.session_state.country_full = st.session_state.df_yr.loc[st.session_state.df_yr['iso3_country']==st.session_state.country,'country'].values[0] if st.session_state.country != 'global' else 'global'

                    filtered_df_country = st.session_state.df_yr[st.session_state.df_yr['iso3_country'] == st.session_state.country] if st.session_state.country != 'global' else st.session_state.df_yr

                    filtered_df_country_sector = filtered_df_country.groupby(['sector','asset_type']).emissions_quantity.sum().reset_index()
                    filtered_df_country_sector['emissions_total'] = filtered_df_country_sector.groupby(['sector'])['emissions_quantity'].transform('sum')
                    filtered_df_country_sector = filtered_df_country_sector.sort_values(['emissions_total','asset_type'], ascending=False)
                    filtered_df_country_sector = filtered_df_country_sector.drop(columns='emissions_total')

                    fig_cty_sec_bar = px.bar(
                        filtered_df_country_sector,
                        x='sector', 
                        y='emissions_quantity', 
                        labels={'emissions_quantity': 'Emissions'},
                        title=f'Top Sectors in {st.session_state.year} | {filtered_df_country_sector.emissions_quantity.sum():,.0f} metric tons',
                        text='emissions_quantity',  # Add labels on top of the bars
                        height=st_layout['height_row'],
                        color='asset_type'
                    )

                    fig_cty_sec_bar.update_traces(textposition='outside', textfont_size=10, texttemplate='%{y:.2s}', hovertemplate='Sector: %{x}<br>Emissions: %{y:.2s}')
                    if trigger_bar_total:
                        fig_cty_sec_bar.update_traces(textposition='inside', textfont_size=10, texttemplate='%{y:.2s}', hovertemplate='Sector: %{x}<br>Emissions: %{y:.2s}')
                        for sector, sector_data in filtered_df_country_sector.groupby('sector'):
                            total_value = sector_data['emissions_quantity'].sum()
                            top_of_bar = sector_data.loc[sector_data['emissions_quantity'] > 0, 'emissions_quantity'].sum()

                            fig_cty_sec_bar.add_annotation(
                                x=sector,
                                y=top_of_bar,
                                text=short_scale_formatter(total_value),  # Total value on top of the bar
                                showarrow=False,
                                font=dict(size=10),
                                yshift=10,  # Adjust the vertical position
                                xanchor='center'
                            )

                    fig_cty_sec_bar.update_xaxes(tickangle=-90)
                    st.plotly_chart(fig_cty_sec_bar, use_container_width=True) 

                with layout_col2:
                    # Section 2: Treemap by Sector/Country
                    st.header("Sector Emissions")

                    layout_col2a, layout_col2b = st.columns(2)  # Create two columns

                    with layout_col2a:
                        sector_list = ['all sectors'] + sorted(st.session_state.df_yr['sector'].unique().tolist())
                        selected_sector = st.selectbox("Select a Sector", options=sector_list, index=4)

                    if selected_sector != st.session_state.sector:
                        st.session_state.sector = selected_sector

                    with layout_col2b:
                        subsector_list = ['all subsectors'] + sorted(st.session_state.df_yr.loc[st.session_state.df_yr['sector']==st.session_state.sector,'subsector'].unique().tolist())
                        selected_subsector = st.selectbox("Select a Subsector", options=subsector_list, index=0)

                    if selected_subsector != st.session_state.subsector:
                        st.session_state.subsector = selected_subsector

                    if st.session_state.subsector == 'all subsectors':
                        filtered_df_sector = st.session_state.df_yr[st.session_state.df_yr['sector'] == st.session_state.sector] if st.session_state.sector != 'all sectors' else st.session_state.df_yr
                    else:
                        filtered_df_sector = st.session_state.df_yr[st.session_state.df_yr['subsector'] == st.session_state.subsector]

                    filtered_df_sector_country = filtered_df_sector.groupby(['iso3_country', 'country', 'asset_type']).emissions_quantity.sum().reset_index()
                    filtered_df_sector_country['emissions_total'] = filtered_df_sector_country.groupby(['iso3_country', 'country'])['emissions_quantity'].transform('sum')

                    filtered_df_sector_country = filtered_df_sector_country.sort_values(['emissions_total','asset_type'], ascending=False)
                    filtered_df_sector_country_r0 = filtered_df_sector_country[:1]
                    if 'non-assets' not in filtered_df_sector_country_r0.asset_type.unique():                        
                        filtered_df_sector_country_r0['asset_type'] = 'non-assets'
                        filtered_df_sector_country_r0['emissions_quantity'] = 0
                        filtered_df_sector_country = pd.concat([filtered_df_sector_country, filtered_df_sector_country_r0], ignore_index=True)

                    filtered_df_sector_country = filtered_df_sector_country.sort_values(['emissions_total','asset_type'], ascending=False)
                    filtered_df_sector_country = filtered_df_sector_country.drop(columns='emissions_total').reset_index(drop=True)

                    #Limited to showing top 50 countries only
                    list_cty_top20 = filtered_df_sector_country.groupby('iso3_country')['emissions_quantity'].sum().sort_values(ascending=False).head(20).index
                    filtered_df_sector_country = filtered_df_sector_country.loc[filtered_df_sector_country['iso3_country'].isin(list_cty_top20),:]

                    fig_sec_cty_bar = px.bar(
                        filtered_df_sector_country,
                        x='country',
                        y='emissions_quantity',
                        title=f'Top 20 Countries in {st.session_state.year} | {filtered_df_sector_country.emissions_quantity.sum():,.0f} metric tons',
                        labels={'emissions_quantity': 'Emissions'},
                        text='emissions_quantity',  # Add labels on top of the bars
                        height=st_layout['height_row'],
                        color='asset_type'
                    )

                    # Set initial range to display only the first 20 countries
                    fig_sec_cty_bar.update_xaxes(range=[-0.5, 19.5], rangeslider=dict(visible=True, thickness=0.05), tickangle=-90)  # Adds a range slider for the x-axis
                    fig_sec_cty_bar.update_layout(xaxis={'categoryorder': 'array', 'categoryarray': filtered_df_sector_country['country'].unique()}, dragmode='pan')

                    fig_sec_cty_bar.update_traces(textposition='outside', textfont_size=10, texttemplate='%{y:.2s}', hovertemplate='Sector: %{x}<br>Emissions: %{y:.2s}')
                    if trigger_bar_total:
                        fig_sec_cty_bar.update_traces(textposition='inside', textfont_size=10, texttemplate='%{y:.2s}', hovertemplate='Sector: %{x}<br>Emissions: %{y:.2s}')
                        for country, country_data in filtered_df_sector_country.groupby('country'):
                            total_value = country_data['emissions_quantity'].sum()
                            top_of_bar = country_data.loc[country_data['emissions_quantity'] > 0, 'emissions_quantity'].sum()

                            fig_sec_cty_bar.add_annotation(
                                x=country,
                                y=top_of_bar,
                                text=short_scale_formatter(total_value),  # Total value on top of the bar
                                showarrow=False,
                                font=dict(size=10),
                                yshift=10,  # Adjust the vertical position
                                xanchor='center'
                            )

                    st.plotly_chart(fig_sec_cty_bar, use_container_width=True)

            # ****** YoY *******
            with st.expander("**Expand to view Country and Sector emissions change YoY**", expanded=False):
                with st.container():        
                    layout_col1, layout_col2 = st.columns(2)  # Create two columns
                        
                    with layout_col1:
                        #Section1: by Sector
                        fds_sec = ['sector']

                        filtered_df_country = st.session_state.df_yr[st.session_state.df_yr['iso3_country'] == st.session_state.country] if st.session_state.country != 'global' else st.session_state.df_yr
                        filtered_df_country_sector = filtered_df_country.groupby(fds_sec).emissions_quantity.sum().reset_index()

                        st.session_state.df_yr1 = st.session_state.df.loc[st.session_state.df['year']==st.session_state.year1,:]
                        filtered_df_country1 = st.session_state.df_yr1[st.session_state.df_yr1['iso3_country'] == st.session_state.country] if st.session_state.country != 'global' else st.session_state.df_yr1
                        filtered_df_country_sector1 = filtered_df_country1.groupby(fds_sec).emissions_quantity.sum().reset_index()

                        filtered_df_country_sector = filtered_df_country_sector.set_index(fds_sec)
                        filtered_df_country_sector1 = filtered_df_country_sector1.set_index(fds_sec)
                        filtered_df_country_sector['emissions_quantity'] = filtered_df_country_sector['emissions_quantity']-filtered_df_country_sector1['emissions_quantity']
                        filtered_df_country_sector.reset_index(inplace=True)

                        filtered_df_country_sector['emissions_total'] = filtered_df_country_sector.groupby(['sector'])['emissions_quantity'].transform('sum')
                        filtered_df_country_sector = filtered_df_country_sector.sort_values(['emissions_total'], ascending=False)
                        if 'asset_type' in fds_sec:
                            filtered_df_country_sector = filtered_df_country_sector.sort_values(['emissions_total','asset_type'], ascending=False)
                        filtered_df_country_sector = filtered_df_country_sector.drop(columns='emissions_total')

                        filtered_df_country, filtered_df_country1, filtered_df_country_sector1 = None, None, None

                        fig_cty_sec_bar = px.bar(
                            filtered_df_country_sector,
                            x='sector', 
                            y='emissions_quantity', 
                            labels={'emissions_quantity': 'Emissions'},
                            title=f'Top Sectors | Change {st.session_state.year} - {st.session_state.year1} | {filtered_df_country_sector.emissions_quantity.sum():,.0f} metric tons',
                            text='emissions_quantity',  # Add labels on top of the bars
                            height=st_layout['height_row'],
                            color='asset_type' if 'asset_type' in fds_sec else None
                        )
                        fig_cty_sec_bar.update_xaxes(tickangle=-90)
                        fig_cty_sec_bar.update_traces(textposition='outside', textfont_size=10, texttemplate='%{y:.2s}', hovertemplate='Sector: %{x}<br>Emissions: %{y:.2s}')

                        st.plotly_chart(fig_cty_sec_bar, use_container_width=True) 

                    with layout_col2:
                        # Section 2: By Country
                        fds_cty = ['iso3_country', 'country']

                        # layout_col2a, layout_col2b = st.columns(2)  # Create two columns

                        if st.session_state.subsector == 'all subsectors':
                            filtered_df_sector = st.session_state.df_yr[st.session_state.df_yr['sector'] == st.session_state.sector] if st.session_state.sector != 'all sectors' else st.session_state.df_yr
                        else:
                            filtered_df_sector = st.session_state.df_yr[st.session_state.df_yr['subsector'] == st.session_state.subsector] if st.session_state.sector != 'all sectors' else st.session_state.df_yr

                        filtered_df_sector_country = filtered_df_sector.groupby(fds_cty).emissions_quantity.sum().reset_index()

                        st.session_state.df_yr1 = st.session_state.df.loc[st.session_state.df['year']==st.session_state.year1,:]
                        if st.session_state.subsector == 'all subsectors':
                            filtered_df_sector1 = st.session_state.df_yr1[st.session_state.df_yr1['sector'] == st.session_state.sector] if st.session_state.sector != 'all sectors' else st.session_state.df_yr1
                        else:
                            filtered_df_sector1 = st.session_state.df_yr1[st.session_state.df_yr1['subsector'] == st.session_state.subsector] if st.session_state.sector != 'all sectors' else st.session_state.df_yr1

                        filtered_df_sector_country1 = filtered_df_sector1.groupby(fds_cty).emissions_quantity.sum().reset_index()

                        filtered_df_sector_country = filtered_df_sector_country.set_index(fds_cty)
                        filtered_df_sector_country1 = filtered_df_sector_country1.set_index(fds_cty)
                        filtered_df_sector_country['emissions_quantity'] = filtered_df_sector_country['emissions_quantity']-filtered_df_sector_country1['emissions_quantity']
                        filtered_df_sector_country.reset_index(inplace=True)

                        filtered_df_sector_country['emissions_total'] = filtered_df_sector_country.groupby(['iso3_country', 'country'])['emissions_quantity'].transform('sum')
                        filtered_df_sector_country = filtered_df_sector_country.sort_values(['emissions_total'], ascending=False)

                        if 'asset_type' in fds_cty:
                            filtered_df_sector_country = filtered_df_sector_country.sort_values(['emissions_total','asset_type'], ascending=False)
                            filtered_df_sector_country_r0 = filtered_df_sector_country[:1]
                            if 'non-assets' not in filtered_df_sector_country_r0.asset_type.unique():                        
                                filtered_df_sector_country_r0['asset_type'] = 'non-assets'
                                filtered_df_sector_country_r0['emissions_quantity'] = 0
                                filtered_df_sector_country = pd.concat([filtered_df_sector_country, filtered_df_sector_country_r0], ignore_index=True)
                            filtered_df_sector_country = filtered_df_sector_country.sort_values(['emissions_total','asset_type'], ascending=False)
                            filtered_df_sector_country = filtered_df_sector_country.drop(columns='emissions_total')

                        filtered_df_sector, filtered_df_sector1, filtered_df_sector_country1 = None, None, None

                        #Limit to top 10 and bottom 10 only
                        filtered_df_sector_country = pd.concat([filtered_df_sector_country[:10], filtered_df_sector_country[-10:]])

                        fig_sec_cty_bar = px.bar(
                            filtered_df_sector_country,
                            x='country',
                            y='emissions_quantity',
                            title=f'Top 10 + Bottom 10 Countries | Change {st.session_state.year} - {st.session_state.year1} | {filtered_df_sector_country.emissions_quantity.sum():,.0f} metric tons',
                            labels={'emissions_quantity': 'Emissions'},
                            text='emissions_quantity',  # Add labels on top of the bars
                            height=st_layout['height_row'],
                            color='asset_type' if 'asset_type' in fds_cty else None
                        )
                
                        # Set initial range to display only the first 20 countries
                        fig_sec_cty_bar.update_xaxes(range=[-0.5, 19.5], rangeslider=dict(visible=True, thickness=0.05), tickangle=-90)  # Adds a range slider for the x-axis
                        fig_sec_cty_bar.update_layout(xaxis={'categoryorder': 'array', 'categoryarray': filtered_df_sector_country['country'].unique()}, dragmode='pan')
                        fig_sec_cty_bar.update_traces(textposition='outside', textfont_size=10, texttemplate='%{y:.2s}', hovertemplate='Country: %{x}<br>Emissions: %{y:.2s}')

                        st.plotly_chart(fig_sec_cty_bar, use_container_width=True)
            # ****** YoY *******

            #Group A1:  Bar Chart 
            # with st.expander("**Expand to view Country and Sector emissions over time**", expanded=False):
            with st.container():
                layout_col1, layout_col2 = st.columns(2)  # Create two columns
                    
                with layout_col1:

                    layout_col1a, layout_col1b = st.columns(2)  # Create two columns

                    with layout_col1a:
                        sector_list = ['all sectors'] + sorted(st.session_state.df_yr['sector'].unique().tolist())
                        selected_sector2 = st.selectbox("Select a Sector", options=sector_list, index=0, key='country_sector2')

                    if selected_sector2 != st.session_state.sector2:
                        st.session_state.sector2 = selected_sector2

                    with layout_col1b:
                        subsector_list = ['all subsectors'] + sorted(st.session_state.df_yr.loc[st.session_state.df_yr['sector']==st.session_state.sector2,'subsector'].unique().tolist())
                        selected_subsector2 = st.selectbox("Select a Subsector", options=subsector_list, index=0, key='country_subsector2')

                    if selected_subsector2 != st.session_state.subsector2:
                        st.session_state.subsector2 = selected_subsector2

                    filtered_df_country_ts = st.session_state.df[st.session_state.df['iso3_country'] == st.session_state.country] if st.session_state.country != 'global' else st.session_state.df
                    if st.session_state.subsector2 == 'all subsectors':
                        filtered_df_country_ts = filtered_df_country_ts[filtered_df_country_ts['sector'] == st.session_state.sector2] if st.session_state.sector2 != 'all sectors' else filtered_df_country_ts
                    else:
                        filtered_df_country_ts = filtered_df_country_ts[filtered_df_country_ts['subsector'] == st.session_state.subsector2]

                    filtered_df_country_ts1 = filtered_df_country_ts.groupby(['year','sector']).emissions_quantity.sum().reset_index()
                    filtered_df_country_ts1 = filtered_df_country_ts1.loc[filtered_df_country_ts1['year']<=st.session_state.year,:]

                    filtered_df_country_ts2 = filtered_df_country_ts.groupby(['year','sector','subsector']).emissions_quantity.sum().reset_index()
                    filtered_df_country_ts2 = filtered_df_country_ts2.loc[filtered_df_country_ts2['year']<=st.session_state.year,:]

                    filtered_df_country_ts0 = filtered_df_country_ts1 if st.session_state.sector2 == 'all sectors' and st.session_state.subsector2 == 'all subsectors' else filtered_df_country_ts2

                    fig_ts_cty_sec_bar = px.bar(
                        filtered_df_country_ts0,
                        x='year', 
                        y='emissions_quantity', 
                        labels={'emissions_quantity': 'Emissions'},
                        title=f"{st.session_state.country_full} Sector Emissions",
                        text='emissions_quantity',  # Add labels on top of the bars
                        height=st_layout['height_row'],
                        color='sector' if st.session_state.sector2 == 'all sectors' and st.session_state.subsector2 == 'all subsectors' else 'subsector',
                        color_discrete_map=ct_color
                    )

                    fig_ts_cty_sec_bar.update_traces(textposition='outside', textfont_size=10, texttemplate='%{y:.2s}', hovertemplate='Sector: %{x}<br>Emissions: %{y:.2s}')
                    if trigger_bar_total:
                        fig_ts_cty_sec_bar.update_traces(textposition='inside', textfont_size=10, texttemplate='%{y:.2s}', hovertemplate='Sector: %{x}<br>Emissions: %{y:.2s}')
                        for year, year_data in filtered_df_country_ts0.groupby('year'):
                            total_value = year_data['emissions_quantity'].sum()
                            top_of_bar = year_data.loc[year_data['emissions_quantity'] > 0, 'emissions_quantity'].sum()

                            fig_ts_cty_sec_bar.add_annotation(
                                x=year,
                                y=top_of_bar,
                                text=short_scale_formatter(total_value),  # Total value on top of the bar
                                showarrow=False,
                                font=dict(size=10),
                                yshift=10,  # Adjust the vertical position
                                xanchor='center'
                            )

                    fig_ts_cty_sec_bar.update_xaxes(tickangle=-90)
                    st.plotly_chart(fig_ts_cty_sec_bar, use_container_width=True) 

                with layout_col2:
                    selected_topRank = st.selectbox("Select a number of countries", options=range(1,11), index=4)

                    if selected_topRank != st.session_state.topRank:
                        st.session_state.topRank = selected_topRank

                    if st.session_state.subsector == 'all subsectors':
                        filtered_df_sector_ts = st.session_state.df[st.session_state.df['sector'] == st.session_state.sector] if st.session_state.sector != 'all sectors' else st.session_state.df
                    else:
                        filtered_df_sector_ts = st.session_state.df[st.session_state.df['subsector'] == st.session_state.subsector] 

                    filtered_df_sector_ts = filtered_df_sector_ts.groupby(['year', 'iso3_country', 'country'])['emissions_quantity'].sum().reset_index()
                    filtered_df_sector_ts['rank'] = filtered_df_sector_ts.groupby(['year'])['emissions_quantity'].transform(
                        lambda x: x.rank(method='min', ascending=False).where(x.notnull()).astype('Int64') if x.notnull().any() else np.nan
                    )

                    filtered_df_sector_ts.loc[filtered_df_sector_ts['rank']>st.session_state.topRank,'iso3_country'] = 'NUL'
                    filtered_df_sector_ts.loc[filtered_df_sector_ts['rank']>st.session_state.topRank,'country'] = 'Rest'

                    filtered_df_sector_ts = filtered_df_sector_ts.groupby(['year','country']).emissions_quantity.sum().reset_index()
                    filtered_df_sector_ts = filtered_df_sector_ts.loc[filtered_df_sector_ts['year']<=st.session_state.year,:]
                    
                    category_order = ['Rest'] + [country for country in filtered_df_sector_ts['country'].unique() if country != 'Rest']

                    fig_ts_cty_bar = px.bar(
                        filtered_df_sector_ts,
                        x='year', 
                        y='emissions_quantity', 
                        labels={'emissions_quantity': 'Emissions'},
                        title=f'Top Countries in {st.session_state.sector} - {st.session_state.subsector}',
                        text='country',  # Add labels on top of the bars
                        height=st_layout['height_row'],
                        color='country',
                        category_orders={'country': category_order}  # Set the order of categories
                    )

                    fig_ts_cty_bar.update_traces(textposition='outside', textfont_size=10, texttemplate='%{y:.2s}', hovertemplate='Sector: %{x}<br>Emissions: %{y:.2s}')
                    if trigger_bar_total:
                        fig_ts_cty_bar.update_traces(textposition='inside', textfont_size=10, texttemplate='%{y:.2s}', hovertemplate='Sector: %{x}<br>Emissions: %{y:.2s}')
                        for year, year_data in filtered_df_sector_ts.groupby('year'):
                            total_value = year_data['emissions_quantity'].sum()
                            top_of_bar = year_data.loc[year_data['emissions_quantity'] > 0, 'emissions_quantity'].sum()

                            fig_ts_cty_bar.add_annotation(
                                x=year,
                                y=top_of_bar,
                                text=short_scale_formatter(total_value),  # Total value on top of the bar
                                showarrow=False,
                                font=dict(size=10),
                                yshift=10,  # Adjust the vertical position
                                xanchor='center'
                            )
                    fig_ts_cty_bar.update_xaxes(tickangle=-90)
                    st.plotly_chart(fig_ts_cty_bar, use_container_width=True) 


            #Group A2:  Line Chart (maybe)
            # with st.container():
            #     layout_col1, layout_col2 = st.columns(2)  # Create two columns
                    
            #     with layout_col1:
            #         # st.header("Country Emissions over time")
            #         filtered_df_country_ts = st.session_state.df[st.session_state.df['iso3_country'] == st.session_state.country] if st.session_state.country != 'global' else st.session_state.df
            #         filtered_df_country_ts = filtered_df_country_ts.groupby(['year']).emissions_quantity.sum().reset_index()
            #         filtered_df_country_ts = filtered_df_country_ts.loc[filtered_df_country_ts['year']<=st.session_state.year,:]

            #         fig_cty_ts = px.line(filtered_df_country_ts, x='year', y=['emissions_quantity'], title=f'{st.session_state.country}')
            #         fig_cty_ts.update_layout(showlegend=False)
            #         st.plotly_chart(fig_cty_ts)

            #     with layout_col2:
            #         # st.header("Sector Emissions over time")
            #         filtered_df_sector_ts = st.session_state.df[st.session_state.df['sector'] == st.session_state.sector] if st.session_state.sector != 'all sectors' else st.session_state.df
            #         filtered_df_sector_ts = filtered_df_sector_ts.groupby(['year']).emissions_quantity.sum().reset_index()
            #         filtered_df_sector_ts = filtered_df_sector_ts.loc[filtered_df_sector_ts['year']<=st.session_state.year,:]

            #         fig_cty_ts = px.line(filtered_df_sector_ts, x='year', y=['emissions_quantity'], title=f'{st.session_state.sector}')
            #         fig_cty_ts.update_layout(showlegend=False)            
            #         st.plotly_chart(fig_cty_ts)

            with st.container():
                layout_col1, layout_col2 = st.columns(2)  # Create two columns

                df_yr_treemap = st.session_state.df_yr 
                
                if st.session_state.choice == 'all sectors (include forestry)':
                    df_yr_treemap = df_yr_treemap.loc[df_yr_treemap['sector'].isin(['forestry-and-land-use'])==False,:]

                with layout_col1:
                    filtered_df_country = df_yr_treemap[df_yr_treemap['iso3_country'] == st.session_state.country] if st.session_state.country != 'global' else df_yr_treemap
                    fig_country = generate_fig(filtered_df_country, ['sector','subsector'], 'emissions_quantity', 'sector')
                    st.plotly_chart(fig_country, use_container_width=True) 

                with layout_col2:
                    filtered_df_sector = df_yr_treemap[df_yr_treemap['sector'] == st.session_state.sector] if st.session_state.sector != 'all sectors' else df_yr_treemap
                    fig_sector = generate_fig(filtered_df_sector, ['subsector','country'], 'emissions_quantity', 'continent_ct')
                    st.plotly_chart(fig_sector, use_container_width=True)

            with st.container():
                st.header(f"Top 10 Emitting Countries by Sector {st.session_state.year}")
                st.write("Forestry sector: country percentage uses only positive emissions.")

                df_top10 = st.session_state.df_yr.groupby(['iso3_country','country','sector'])['emissions_quantity'].sum().reset_index()

                df_top10_all = st.session_state.df_yr.groupby(['iso3_country','country'])['emissions_quantity'].sum().reset_index()
                df_top10_all['sector'] = 'all sectors'

                df_top10 = pd.concat([df_top10_all, df_top10], ignore_index=True)

                # df_top10['rank'] = df_top10.groupby(['sector'])['emissions_quantity'].rank(method='min', ascending=False).astype(int)
                df_top10['rank'] = df_top10.groupby('sector')['emissions_quantity'].transform(
                    lambda x: x.rank(method='min', ascending=False).astype(int) if x.notnull().any() else np.nan
                )

                group_total = df_top10.groupby(['sector'])['emissions_quantity'].transform(lambda x: x[x > 0].sum())
                df_top10['emissions_pct'] = ((df_top10['emissions_quantity'] / group_total) * 100).round(2)
                df_top10['emissions_total'] = df_top10.groupby(['sector'])['emissions_quantity'].transform('sum').astype(int)

                df_top10 = df_top10.loc[df_top10['rank']<=10,:]
                df_top10['contents'] = df_top10['country'] + df_top10['emissions_pct'].apply(lambda x: " ({:,.0f}%)".format(x))
                df_top10 = df_top10.pivot_table(index=['sector','emissions_total'], columns='rank',values='contents', aggfunc='first')

                df_top10 = df_top10.sort_values(by='sector', key=lambda x: x == 'all sectors', ascending=False)

                st.dataframe(df_top10, use_container_width=True, height=st_layout['height_row']-80)

            with st.expander("**Expand to view SubSectors**", expanded=False):
                with st.container():
                    st.header(f"Top 10 Emitting Countries by SubSector {st.session_state.year}")

                    df_top10 = st.session_state.df_yr.groupby(['iso3_country','country','sector','subsector'])['emissions_quantity'].sum().reset_index()

                    # df_top10['rank'] = df_top10.groupby(['sector','subsector'])['emissions_quantity'].rank(method='min', ascending=False).astype(int)
                    df_top10['rank'] = df_top10.groupby(['sector','subsector'])['emissions_quantity'].transform(
                        lambda x: x.rank(method='min', ascending=False).astype(int) if x.notnull().any() else np.nan
                    )

                    group_total = df_top10.groupby(['sector','subsector'])['emissions_quantity'].transform(lambda x: x[x > 0].sum())
                    df_top10['emissions_pct'] = ((df_top10['emissions_quantity'] / group_total) * 100).round(2)
                    df_top10['emissions_total'] = df_top10.groupby(['sector','subsector'])['emissions_quantity'].transform('sum')

                    df_top10 = df_top10.loc[df_top10['rank']<=10,:]
                    df_top10['contents'] = df_top10['country'] + df_top10['emissions_pct'].apply(lambda x: " ({:,.0f}%)".format(x))
                    df_top10 = df_top10.pivot_table(index=['sector','subsector','emissions_total'], columns='rank',values='contents', aggfunc='first')

                    st.dataframe(df_top10, use_container_width=True, height=st_layout['height_row']-80)
                    st.write("note:  forestry percentage uses positive emissions only")

            # ****** Change YoY - START ********
            st.session_state.df_top10 = None
            with st.container():
                st.header(f"Top 10 Emitting Countries YoY {st.session_state.year} - {st.session_state.year1}")

                df_top10 = st.session_state.df_yr.groupby(['iso3_country','country','sector'])['emissions_quantity'].sum().reset_index()
                df_top10_all = st.session_state.df_yr.groupby(['iso3_country','country'])['emissions_quantity'].sum().reset_index()
                df_top10_all['sector'] = 'all sectors'
                df_top10a = pd.concat([df_top10_all, df_top10], ignore_index=True).set_index(['iso3_country','country','sector'])

                df_top10 = st.session_state.df.loc[st.session_state.df['year']==st.session_state.year1,:].groupby(['iso3_country','country','sector'])['emissions_quantity'].sum().reset_index()
                df_top10_all = st.session_state.df.loc[st.session_state.df['year']==st.session_state.year1,:].groupby(['iso3_country','country'])['emissions_quantity'].sum().reset_index()
                df_top10_all['sector'] = 'all sectors'
                df_top10b = pd.concat([df_top10_all, df_top10], ignore_index=True).set_index(['iso3_country','country','sector'])

                df_top10 = df_top10a.copy()
                df_top10['emissions_quantity'] = df_top10a['emissions_quantity'] - df_top10b['emissions_quantity']
                df_top10['emissions_quantity_pct'] = df_top10a['emissions_quantity']/df_top10b['emissions_quantity']-1
                df_top10['emissions_quantity_pct'] = df_top10['emissions_quantity_pct'].replace([np.inf, -np.inf], np.nan).fillna(0)
                df_top10['emissions_total'] = df_top10.groupby(['sector'])['emissions_quantity'].transform('sum').astype(int)
                df_top10['emissions_total_pct'] = df_top10a.groupby(['sector'])['emissions_quantity'].transform('sum')/df_top10b.groupby(['sector'])['emissions_quantity'].transform('sum')-1
                df_top10['emissions_total_pct'] = df_top10['emissions_total_pct'].replace([np.inf, -np.inf], np.nan).fillna(0)
                df_top10['emissions_total_pct'] = df_top10['emissions_total_pct'].apply(lambda x: "{:.2f}%".format(x * 100))

                df_top10.reset_index(inplace=True)
                df_top10a, df_top10b = None, None

                st.session_state.df_top10 = df_top10.copy()

                df_top10['rank'] = df_top10.groupby('sector')['emissions_quantity'].transform(
                    lambda x: x.rank(method='min', ascending=False).astype(int) if x.notnull().any() else np.nan
                )

                df_top10 = df_top10.loc[df_top10['rank']<=10,:]
                if df_top10['emissions_quantity'].max() < 1000000:
                    df_top10['contents'] = df_top10['country'] + df_top10['emissions_quantity'].apply(lambda x: " ({:,.1f}k)".format(x / 1_000))
                else:
                    df_top10['contents'] = df_top10['country'] + df_top10['emissions_quantity'].apply(lambda x: " ({:,.1f}M)".format(x / 1_000_000))
                df_top10 = df_top10.pivot_table(index=['sector','emissions_total'], columns='rank',values='contents', aggfunc='first')

                df_top10 = df_top10.sort_values(by='sector', key=lambda x: x == 'all sectors', ascending=False)

                st.dataframe(df_top10, use_container_width=True, height=st_layout['height_row']-80)

            with st.container():
                st.header(f"Bottom 10 Emitting Countries YoY {st.session_state.year} - {st.session_state.year1}")

                df_top10 = st.session_state.df_top10.copy()

                df_top10['rank'] = df_top10.groupby('sector')['emissions_quantity'].transform(
                    lambda x: x.rank(method='min', ascending=True).astype(int) if x.notnull().any() else np.nan
                )

                df_top10 = df_top10.loc[df_top10['rank']<=10,:]
                if df_top10['emissions_quantity'].max() < 1000000:
                    df_top10['contents'] = df_top10['country'] + df_top10['emissions_quantity'].apply(lambda x: " ({:,.1f}k)".format(x / 1_000))
                else:
                    df_top10['contents'] = df_top10['country'] + df_top10['emissions_quantity'].apply(lambda x: " ({:,.1f}M)".format(x / 1_000_000))
                df_top10 = df_top10.pivot_table(index=['sector','emissions_total'], columns='rank',values='contents', aggfunc='first')

                df_top10 = df_top10.sort_values(by='sector', key=lambda x: x == 'all sectors', ascending=False)

                st.dataframe(df_top10, use_container_width=True, height=st_layout['height_row']-80)

            with st.expander("**Expand to view Top/Bottom10 YoY %**", expanded=False):
                with st.container():
                    st.header(f"Top 10 Emitting Countries YoY % {st.session_state.year} - {st.session_state.year1}")

                    df_top10 = st.session_state.df_top10.copy()

                    df_top10['rank'] = df_top10.groupby('sector')['emissions_quantity_pct'].transform(
                        lambda x: x.rank(method='min', ascending=False).astype(int) if x.notnull().any() else np.nan
                    )

                    df_top10 = df_top10.loc[df_top10['rank']<=10,:]
                    df_top10['contents'] = df_top10['country'] + df_top10['emissions_quantity_pct'].apply(lambda x: " ({:,.1f}%)".format(x))
                    df_top10 = df_top10.pivot_table(index=['sector','emissions_total_pct'], columns='rank',values='contents', aggfunc='first')

                    df_top10 = df_top10.sort_values(by='sector', key=lambda x: x == 'all sectors', ascending=False)

                    st.dataframe(df_top10, use_container_width=True, height=st_layout['height_row']-80)

                with st.container():
                    st.header(f"Bottom 10 Emitting Countries YoY % {st.session_state.year} - {st.session_state.year1}")

                    df_top10 = st.session_state.df_top10.copy()

                    df_top10['rank'] = df_top10.groupby('sector')['emissions_quantity_pct'].transform(
                        lambda x: x.rank(method='min', ascending=True).astype(int) if x.notnull().any() else np.nan
                    )

                    df_top10 = df_top10.loc[df_top10['rank']<=10,:]
                    df_top10['contents'] = df_top10['country'] + df_top10['emissions_quantity_pct'].apply(lambda x: " ({:,.1f}%)".format(x))
                    df_top10 = df_top10.pivot_table(index=['sector','emissions_total_pct'], columns='rank',values='contents', aggfunc='first')

                    df_top10 = df_top10.sort_values(by='sector', key=lambda x: x == 'all sectors', ascending=False)

                    st.dataframe(df_top10, use_container_width=True, height=st_layout['height_row']-80)
                    
            # ****** Change YoY - END ********

            # ****** Top Assets by Country - START ********
            with st.container():
                st.header("Top 10 Emitting Assets by Country-Sector")

                layout_col1a, layout_col1b = st.columns(2)  # Create two columns

                with layout_col1a:
                    country_list = ['g20'] + sorted(st.session_state.df_asset['country'].unique().tolist())
                    selected_topAsset = st.selectbox("Select a Country", options=country_list, key='country_asset')

                if selected_topAsset != 'g20':
                    selected_topAsset = st.session_state.df_asset.loc[st.session_state.df_asset['country']==selected_topAsset,'iso3_country'].values[0]

                if selected_topAsset != st.session_state.topAsset:
                    st.session_state.topAsset = selected_topAsset

                with layout_col1b:
                    selected_topAssetField = st.selectbox("Select data type", options=['emissions_quantity','emissions_quantity_diff'], index=0, key='country_asset_field')

                if selected_topAssetField != st.session_state.topAssetField:
                    st.session_state.topAssetField = selected_topAssetField

                filtered_df_asset = st.session_state.df_asset[st.session_state.df_asset['iso3_country'] == st.session_state.topAsset] if st.session_state.topAsset != 'g20' else st.session_state.df_asset
                filtered_df_asset = filtered_df_asset.loc[filtered_df_asset['year']<=st.session_state.year,:]
                filtered_df_asset[st.session_state.topAssetField] = filtered_df_asset[st.session_state.topAssetField].replace([np.inf, -np.inf], np.nan).fillna(0).astype(int)

                filtered_df_asset_ts = filtered_df_asset.pivot_table(index=['iso3_country','sector','subsector','asset_type','asset_name','asset_id'], columns='year', values=[st.session_state.topAssetField], aggfunc='sum')

                if filtered_df_asset_ts.empty == False:
                    filtered_df_asset_ts.columns = filtered_df_asset_ts.columns.droplevel(0)
                    filtered_df_asset_ts = filtered_df_asset_ts.sort_values(by=min(st.session_state.year, filtered_df_asset.year.max()), ascending=False)
                    
                st.dataframe(filtered_df_asset_ts, use_container_width=True, height=st_layout['height_row']-80)

            # ****** Top Assets by Country - END ********

            # ****** Top 500 Assets Globally - START ********
            with st.container():
                st.header("Top 500 Assets Globally")
                filtered_df_top500 = st.session_state.df_top500.set_index(['iso3_country','sector','subsector','asset_type','asset_name','asset_id'])

                filtered_df_top500 = filtered_df_top500.replace([np.inf, -np.inf], np.nan).fillna(0)
                filtered_df_top500 = filtered_df_top500.astype(int)
                filtered_df_top500 = filtered_df_top500.loc[:, [x for x in filtered_df_top500.columns.tolist() if int(x) <= st.session_state.year]]

                year_list = sorted([int(x) for x in filtered_df_top500.columns.tolist()], reverse=True)
                selected_rankYear = st.selectbox("Sort by", options=year_list, key='year_rank')

                if selected_rankYear != st.session_state.rankYear:
                    st.session_state.rankYear = selected_rankYear

                filtered_df_top500 = filtered_df_top500.sort_values(by=str(st.session_state.rankYear), ascending=False).reset_index()
                filtered_df_top500.index += 1
                filtered_df_top500['rank'] = filtered_df_top500.index
                filtered_df_top500a = filtered_df_top500.set_index(['rank','iso3_country','sector','subsector','asset_type','asset_name','asset_id']).head(500)
                
                st.dataframe(filtered_df_top500a, use_container_width=True, height=st_layout['height_row']-80)

            # ****** Top 500 Assets Globally - END ********


            with st.container():
                # st.markdown(f"<h2 style='display: inline-block; vertical-align: middle;'>Climate TRACE Emissions Data Pivot Table {st.session_state.year}</h2>", unsafe_allow_html=True)
                st.header("Comprehensive Emissions Table " + str(st.session_state.year))
                
                df_tb = st.session_state.df_yr[['continent_ct','iso3_country','country','sector','subsector','asset_type','emissions_quantity','activity','capacity']]
                df_tb = df_tb.sort_values(['continent_ct','iso3_country','sector','subsector','asset_type'])
                df_tb.reset_index(drop=True, inplace=True)
                csv_tb = df_tb.to_csv(index=False)

                st.download_button(
                    label="Download CSV",
                    data=csv_tb,
                    file_name='table_data.csv',
                    mime='text/csv'
                )

                # # Build grid options for hierarchical row grouping
                fds_row = ['continent_ct','iso3_country','country','sector','subsector','asset_type']
                fds_row = ['continent_ct','iso3_country','country']
                fds_col = ['year']
                fds_val = ['emissions_quantity','count','activity']
                display_fds = fds_col + fds_row + fds_val

                df_tb = st.session_state.df[display_fds]
                df_tb = df_tb.loc[df_tb['year'].isin([st.session_state.year,st.session_state.year1]),:]
                df_tb.rename(columns={'emissions_quantity': 'emissions', 'count': '#assets'}, inplace=True)
            
                fds_val1 = ['emissions','activity']  
                df_tb = df_tb.pivot_table(index=fds_row, columns=fds_col, values=fds_val1, aggfunc='sum')
    
                df_tb.columns = ['_'.join([str(x) for x in col]).strip() for col in df_tb.columns]
                df_tb['emissions_' + '-'.join([str(st.session_state.year), str(st.session_state.year1)])] = df_tb['_'.join(["emissions",str(st.session_state.year)])] - df_tb['_'.join(["emissions",str(st.session_state.year1)])]
                df_tb['activity_' + '-'.join([str(st.session_state.year), str(st.session_state.year1)])] = df_tb['_'.join(["activity",str(st.session_state.year)])] - df_tb['_'.join(["activity",str(st.session_state.year1)])]
                df_tb.reset_index(inplace=True)

                df_tb = df_tb.sort_values('_'.join(["emissions", str(st.session_state['year'])]), ascending=False)
                df_tb = df_tb.set_index(['continent_ct','iso3_country','country'])
                df_tb = df_tb[sorted(df_tb.columns.tolist())]
                df_tb = df_tb.astype(int)
                st.dataframe(df_tb, use_container_width=True, height=st_layout['height_row']-80)

                # dict_fds_agg = {'emissions': [
                #         '_'.join(["emissions",str(st.session_state.year)]),
                #         '_'.join(["emissions",str(st.session_state.year1)]),
                #         'emissions_' + '-'.join([str(st.session_state.year), str(st.session_state.year1)])
                #     ],
                #     'activity': [
                #         '_'.join(["activity",str(st.session_state.year)]),
                #         '_'.join(["activity",str(st.session_state.year1)]),
                #         'activity_' + '-'.join([str(st.session_state.year), str(st.session_state.year1)]),
                #     ]   
                # }

                # fds_reordered = fds_row 
                # for v in dict_fds_agg.values():
                #     fds_reordered += v

                # def js_tb(fds_agg):
                #     percentage_js = JsCode(f"""
                #         function(params) {{
                #             if (params.node.groupData) {{
                #                 var value1Field = '{fds_agg[0]}';  // Dynamic column name for Value1
                #                 var value2Field = '{fds_agg[1]}';  // Dynamic column name for Value2

                #                 var totalValue1 = params.node.aggData[value1Field] || 0;  // Aggregated data for dynamic column name
                #                 var totalValue2 = params.node.aggData[value2Field] || 0;  // Aggregated data for dynamic column name

                #                 if (totalValue2 !== 0) {{
                #                     return ((totalValue1 / totalValue2 -1)* 100).toFixed(1) + '%';
                #                 }} else {{
                #                     return '0%';
                #                 }}
                #             }} else {{
                #                 return '';
                #             }}
                #         }}
                #         """)
                #     return percentage_js

                # gb = GridOptionsBuilder.from_dataframe(df_tb[fds_reordered])
                # gb.configure_side_bar()  # Add a sidebar for filtering

                # gridOptions = gb.build()

                # gridOptions['columnDefs'] = [
                #     {'headerName': 'continent', 'field': 'continent_ct', 'rowGroup': True, 'hide': True},
                #     {'headerName': 'country', 'field': 'country', 'rowGroup': True, 'showRowGroup': 'country', 'filter': 'agTextColumnFilter'},
                #     {'headerName': 'sector', 'field': 'sector', 'rowGroup': True, 'showRowGroup': 'sector', 'filter': 'agTextColumnFilter'},
                #     {'headerName': 'subsector', 'field': 'subsector', 'rowGroup': True, 'showRowGroup': 'subsector', 'filter': 'agTextColumnFilter'},
                #     {'headerName': 'asset_type', 'field': 'asset_type', 'rowGroup': True, 'showRowGroup': 'asset_type', 'filter': 'agTextColumnFilter'},
                # ]

                # gridOptions['columnDefs'] += [
                #     {'headerName': x, 'field': x, 'suppressAggFuncInHeader': True,  'type': ["numericColumn", "customNumericFormat"], 'aggFunc': 'sum', 'precision': 0, 'valueFormatter': "x.toLocaleString('en-US', {minimumFractionDigits: 0, maximumFractionDigits: 0})"}
                #     for x in dict_fds_agg['emissions']
                # ]

                # gridOptions['columnDefs'] += [    
                #     {'headerName': 'emissions_%', 'field': 'emissions_change', 'valueGetter': js_tb(dict_fds_agg['emissions'][:2]), 'cellStyle': {'textAlign': 'right'}, 'headerClass': 'header-align-right'},
                # ]

                # # *** activity ***
                # # def custom_agg_func(params):
                # #     # Custom aggregation logic that restricts sum at specific group levels
                # #     if params.node.group and params.node.field in ['sector']:  # Stop at the sector level
                # #         return sum([x[params.column.getColId()] for x in params.values])
                # #     return None
            
                # # gridOptions['columnDefs'] += [
                # #     {'headerName': x, 'field': x, 'suppressAggFuncInHeader': True, 'type': ["numericColumn", "customNumericFormat"], 'aggFunc': custom_agg_func, 'precision': 0, 'valueFormatter': "x.toLocaleString('en-US', {minimumFractionDigits: 0, maximumFractionDigits: 0})"}
                # #     for x in dict_fds_agg['activity']
                # # ]

                # # gridOptions['columnDefs'] += [
                # #     {'headerName': x, 'field': x, 'suppressAggFuncInHeader': True,  'type': ["numericColumn", "customNumericFormat"], 'aggFunc': 'sum', 'precision': 0, 'valueFormatter': "x.toLocaleString('en-US', {minimumFractionDigits: 0, maximumFractionDigits: 0})"}
                # #     for x in dict_fds_agg['activity']
                # # ]

                # # gridOptions['columnDefs'] += [    
                # #     {'headerName': 'activitys_%', 'field': 'activity_change', 'valueGetter': js_tb(dict_fds_agg['activity'][:2]), 'cellStyle': {'textAlign': 'right'}, 'headerClass': 'header-align-right'},
                # # ]

                # gridOptions['domLayout'] = 'autoHeight'  # Automatically adjust the grid height
                # gridOptions['suppressHorizontalScroll'] = True  # Suppress the horizontal scroll to fit columns to the grid width
                # gridOptions['defaultColDef'] = {'flex': 1}  # Set flex grow for columns to auto-size

                # df_agGrid = AgGrid(df_tb[fds_reordered].copy(), gridOptions=gridOptions, enable_enterprise_modules=True, allow_unsafe_jscode=True) #,  fit_columns_on_grid_load=True, update_mode=GridUpdateMode.NO_UPDATE

                # grid_data = pd.DataFrame(df_agGrid['data'])

                # # # Convert the DataFrame to CSV
                # # csv = grid_data.to_csv(index=False)

                # # # Add a download button above the table
                # # st.download_button(
                # #     label="Download CSV",
                # #     data=csv,
                # #     file_name='aggrid_data.csv',
                # #     mime='text/csv'
                # # )

    with layout_tab2:
        st.header("Climate TRACE Emissions Inventory Comparison")

        layout_col1, layout_col2, layout_col3 = st.columns(3)
        with layout_col1:
            # country_list = ['global'] + sorted(st.session_state.df_yr['country'].unique().tolist())
            country_list = sorted(st.session_state.df_yr['country'].unique().tolist())
            cty_selected = st.session_state.df_yr.loc[st.session_state.df_yr['iso3_country']==st.session_state.country_comp,'country'].values[0] if st.session_state.country_comp != False else 'global'

            selected_country_comp = st.selectbox("Select a Country", options=country_list, index=country_list.index(cty_selected), key='comp_box_country')
            if selected_country_comp != 'global':
                selected_country_comp = st.session_state.df_yr.loc[st.session_state.df_yr['country']==selected_country_comp,'iso3_country'].values[0]
            else:
                selected_country_comp = False

            if selected_country_comp != st.session_state.country_comp:
                st.session_state.country_comp = selected_country_comp
                st.session_state.chart_comp_loaded = False

        with layout_col2:
            all_years = sorted(st.session_state.df.year.unique().tolist(), reverse=True)
            selected_year_comp = st.selectbox("Select a Year", options=all_years, index=all_years.index(st.session_state.year_comp), key='comp_box_year')

            if selected_year_comp != st.session_state.year_comp:
                st.session_state.year_comp = selected_year_comp
                st.session_state.chart_comp_loaded = False

        with layout_col3:
            selected_gas_comp = st.selectbox("Select a Gas", options=gas_type, index=gas_type.index(st.session_state.gas_comp), key='comp_box_gas')

            if selected_gas_comp != st.session_state.gas_comp:
                st.session_state.gas_comp = selected_gas_comp
                st.session_state.chart_comp_loaded = False

                st.rerun()

        #UNFCCC=True, EDGAR=True, CAIT=True, PIK=True, GCP=True, CarbonMonitor=True
        if st.button("Load Chart"):
            st.session_state.chart_comp_loaded = True

        if st.session_state.chart_comp_loaded:
            # if st.session_state.country_comp != st.session_state.cp.country:
            st.session_state.cp = CountryPlotting(st.session_state.country_comp)
            fig_comp= st.session_state.cp.single_year_comparison_sectors(st.session_state.gas_comp, st.session_state.year_comp, EDGAR=True,lulucf=True)
            st.session_state.cp = None

            st.plotly_chart(fig_comp, use_container_width=True)            
        else:
            st.write("Click the button to load the chart.")
    