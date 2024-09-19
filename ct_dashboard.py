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
from datetime import datetime
import numpy as np

# Load the CSV files from the current directory
csv_directory = './data'  # Current directory
csv_files = [f for f in os.listdir(csv_directory) if f.endswith('.csv') and 'ct_assets_' in f]
csv_files = sorted(csv_files, reverse=True)
all_years = []

# Basic setup
st_layout = {'width_col': 1000,
             'height_row':  500}

st.set_page_config(layout="wide")

st.markdown("""
    <style>
    .map-container {
        width: 100%;  /* Make the map container full width */
        height: 500px; /* Set a fixed height for the map */
    }
    </style>
""", unsafe_allow_html=True)

# Ensure there's at least one CSV file
if not csv_files:
    st.error("No CSV files found in the directory.")
else:
    # Initialize session state variables if they don't exist
    if 'file' not in st.session_state:
        st.session_state.file = csv_files[0] #first one is the latest updated file; all years get lumped into one
        st.session_state.df = pd.read_csv(os.path.join(csv_directory, st.session_state.file))
        # st.session_state.df_exf = st.session_state.df.loc[st.session_state.df['sector'].isin(['forestry-and-land-use'])==False,:]

    if 'choice' not in st.session_state:
        st.session_state.choice = 'all sectors' # or 'ex-forestry'

    if 'year' not in st.session_state:
        all_years = sorted(st.session_state.df.year.unique().tolist(), reverse=True)
        st.session_state.year = all_years[1]
        st.session_state.year1 = all_years[2]
        st.session_state.df_yr = st.session_state.df.loc[st.session_state.df['year']==int(st.session_state.year),:]
        # st.session_state.df_exf_yr = st.session_state.df_exf.loc[st.session_state.df_exf['year']==int(st.session_state.year),:]

    if 'country' not in st.session_state:
        st.session_state.country = "global"

    if 'sector' not in st.session_state:
        st.session_state.sector = "all sectors"

    # File selection dropdown
    with st.container():
        match = re.search(r"\['(.*?)'\]_(\d{8})", st.session_state.file)

        if match:
            gas_type = match.group(1).upper()
            date_str = match.group(2)
            st.header(f"Climate TRACE emissions data [{gas_type}] - {datetime.strptime(date_str, '%Y%m%d').strftime('%b, %d, %Y')}")
        else:
            st.header(f"Climate TRACE emissions data")

        layout_col1, layout_col2 = st.columns(2)  # Create two columns
        with layout_col1:
            selected_file = st.selectbox("Select a CSV file", options=csv_files, index=csv_files.index(st.session_state.file))

        with layout_col2:
            selected_choice = st.selectbox("Select data type", options=['all sectors', 'ex-forestry'], index=0)

    if selected_file != st.session_state.file:
        st.session_state.file = selected_file

        st.session_state.df = pd.read_csv(os.path.join(csv_directory, st.session_state.file))
        st.session_state.df_yr = st.session_state.df.loc[st.session_state.df['year']==int(st.session_state.year),:]

    if selected_choice != st.session_state.choice:
        st.session_state.choice = selected_choice

        if st.session_state.choice == 'ex-forestry':
            st.session_state.df = st.session_state.df.loc[st.session_state.df['sector'].isin(['forestry-and-land-use'])==False,:]
            st.session_state.df_yr = st.session_state.df.loc[st.session_state.df['year']==int(st.session_state.year),:]
        else:
            st.session_state.df = pd.read_csv(os.path.join(csv_directory, st.session_state.file))
            st.session_state.df_yr = st.session_state.df.loc[st.session_state.df['year']==int(st.session_state.year),:]

    # Year selection dropdown
    with st.container():
        layout_col1, layout_col2 = st.columns(2)  # Create two columns

        all_years = sorted(st.session_state.df.year.unique().tolist(), reverse=True)
            
        with layout_col1:
            selected_year = st.selectbox("Select default year", options=all_years, index=1)

        if selected_year != st.session_state.year:
            st.session_state.year = selected_year
            st.session_state.df_yr = st.session_state.df.loc[st.session_state.df['year']==int(st.session_state.year),:]
            # st.session_state.df_exf_yr = st.session_state.df_exf.loc[st.session_state.df_exf['year']==int(st.session_state.year),:]

            st.rerun()

        with layout_col2:
            selected_year_comp = st.selectbox("Select comp year", options=all_years, index=2)

        if selected_year_comp != st.session_state.year1:
            st.session_state.year1 = selected_year_comp

    # Formatting function for generating a treemap figure
    def generate_fig(data, path, value, color):
        total_value = int(data[value].sum())

        fig = px.treemap(data, path=path, values=value, color=color,  maxdepth=2,
                         title='Treemap for Climate TRACE data')

        fig.update_layout(
            width=st_layout['width_col'],
            height=st_layout['height_row'],
            margin=dict(t=0, l=0, b=0, r=0),  # Remove margins around the treemap
            paper_bgcolor='white',  # Background color of the paper
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
                line=dict(width=0)  # Reduce outline width
            ),
        )

        return fig

    # Layout:  First Row
    with st.container():
        layout_col1, layout_col2 = st.columns(2)  # Create two columns

        with layout_col1:
            st.header("Global Emissions")
            # st.write("Include Forestry")

            fig_all_sec_bar = px.bar(st.session_state.df.loc[st.session_state.df['year']<=st.session_state.year,:].groupby(['year','sector']).emissions_quantity.sum().reset_index(), 
                        x='year', 
                        y='emissions_quantity', 
                        color='sector',  # This will create the stack
                        )

            st.plotly_chart(fig_all_sec_bar)

        with layout_col2:
            # Set up the title of the Streamlit app
            st.header("Country Hotspot")
            # st.write("Exclude Forestry")

            # Load internal GADM boundary CSV into a DataFrame
            df_gadm = pd.read_csv(os.path.join(csv_directory, 'ct_gadm_cty_point_20240915.csv'))
            df_gadm['geometry'] = df_gadm['geometry'].apply(wkt.loads)
            gdf_gadm = gpd.GeoDataFrame(df_gadm, geometry='geometry')

            df_tb = st.session_state.df[['year','iso3_country','country','emissions_quantity']]            
            df_tb = df_tb.loc[df_tb['year'].isin([st.session_state.year,st.session_state.year1]),:]
            df_tb.rename(columns={'emissions_quantity': 'emissions'}, inplace=True)
            df_tb = df_tb.pivot_table(index=['iso3_country','country'], columns='year', values='emissions').reset_index()

            fds_diff = 'emissions_' + '-'.join([str(st.session_state.year), str(st.session_state.year1)])
            df_tb[fds_diff] = df_tb[st.session_state.year] - df_tb[st.session_state.year1]

            #Coloring
            custom_percentiles = [0, 0.001, 0.02, 0.1, 0.15, 0.5, 0.85, 0.95, 0.99, 0.999, 1.0] 

            # bins = pd.qcut(df_tb[fds_diff], q=10)
            bins = pd.qcut(df_tb[fds_diff], q=custom_percentiles)

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
            size_bins = pd.qcut(df_tb[st.session_state.year], q=custom_percentiles, labels=range(5, 15)) 
            df_tb['Size'] = size_bins

            #Plot
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

            folium.LayerControl().add_to(folium_map)
            st_folium(folium_map, width=st_layout['width_col'], height=st_layout['height_row'])

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
                title=f'Top Sectors in {st.session_state.year}',
                text='emissions_quantity',  # Add labels on top of the bars
                height=st_layout['height_row'],
                color='asset_type'
            )
            fig_cty_sec_bar.update_xaxes(tickangle=-90)
            fig_cty_sec_bar.update_traces(textposition='outside', textfont_size=10, texttemplate='%{y:.2s}', hovertemplate='Sector: %{x}<br>Emissions: %{y:.2s}')

            st.plotly_chart(fig_cty_sec_bar, use_container_width=True) 

        with layout_col2:
            # Section 2: Treemap by Sector/Country
            st.header("Sector Emissions")

            sector_list = ['all sectors'] + sorted(st.session_state.df_yr['sector'].unique().tolist())
            selected_sector = st.selectbox("Select a Sector", options=sector_list, index=1)

            if selected_sector != st.session_state.sector:
                st.session_state.sector = selected_sector

            filtered_df_sector = st.session_state.df_yr[st.session_state.df_yr['sector'] == st.session_state.sector] if st.session_state.sector != 'all sectors' else st.session_state.df_yr

            filtered_df_sector_country = filtered_df_sector.groupby(['iso3_country', 'country', 'asset_type']).emissions_quantity.sum().reset_index()
            filtered_df_sector_country['emissions_total'] = filtered_df_sector_country.groupby(['iso3_country', 'country'])['emissions_quantity'].transform('sum')
            filtered_df_sector_country = filtered_df_sector_country.sort_values(['emissions_total','asset_type'], ascending=False)
            filtered_df_sector_country = filtered_df_sector_country.drop(columns='emissions_total')

            fig_sec_cty_bar = px.bar(
                filtered_df_sector_country,
                x='country',
                y='emissions_quantity',
                title=f'Top 20 Countries in {st.session_state.year}',
                labels={'emissions_quantity': 'Emissions'},
                text='emissions_quantity',  # Add labels on top of the bars
                height=st_layout['height_row'],
                color='asset_type'
            )
    
            # Set initial range to display only the first 20 countries
            fig_sec_cty_bar.update_xaxes(range=[-0.5, 19.5], rangeslider=dict(visible=True, thickness=0.05), tickangle=-90)  # Adds a range slider for the x-axis
            fig_sec_cty_bar.update_layout(xaxis=dict(tickmode='linear'), dragmode='pan')
            fig_sec_cty_bar.update_traces(textposition='outside', textfont_size=10, texttemplate='%{y:.2s}', hovertemplate='Country: %{x}<br>Emissions: %{y:.2s}')

            st.plotly_chart(fig_sec_cty_bar, use_container_width=True)

    #Group A1:  Bar Chart 
    with st.expander("**Emissions by Country and Sector over time**", expanded=False):
        with st.container():
            layout_col1, layout_col2 = st.columns(2)  # Create two columns
                
            with layout_col1:
                # st.header("Country Emissions over time")
                filtered_df_country_ts = st.session_state.df[st.session_state.df['iso3_country'] == st.session_state.country] if st.session_state.country != 'global' else st.session_state.df
                filtered_df_country_ts = filtered_df_country_ts.groupby(['year','sector']).emissions_quantity.sum().reset_index()
                filtered_df_country_ts = filtered_df_country_ts.loc[filtered_df_country_ts['year']<=st.session_state.year,:]

                fig_ts_cty_sec_bar = px.bar(
                    filtered_df_country_ts,
                    x='year', 
                    y='emissions_quantity', 
                    labels={'emissions_quantity': 'Emissions'},
                    title=f'{st.session_state.country} Sector Emissions',
                    text='emissions_quantity',  # Add labels on top of the bars
                    height=st_layout['height_row'],
                    color='sector'
                )
                fig_ts_cty_sec_bar.update_xaxes(tickangle=-90)
                fig_ts_cty_sec_bar.update_traces(textposition='outside', textfont_size=10, texttemplate='%{y:.2s}', hovertemplate='Sector: %{x}<br>Emissions: %{y:.2s}')
                st.plotly_chart(fig_ts_cty_sec_bar, use_container_width=True) 

            with layout_col2:
                # st.header("Sector Emissions over time")
                filtered_df_sector_ts = st.session_state.df[st.session_state.df['sector'] == st.session_state.sector] if st.session_state.sector != 'all sectors' else st.session_state.df

                filtered_df_sector_ts = filtered_df_sector_ts.groupby(['year', 'iso3_country', 'country'])['emissions_quantity'].sum().reset_index()
                filtered_df_sector_ts['rank'] = filtered_df_sector_ts.groupby(['year'])['emissions_quantity'].transform(
                    lambda x: x.rank(method='min', ascending=False).where(x.notnull()).astype('Int64') if x.notnull().any() else np.nan
                )

                filtered_df_sector_ts.loc[filtered_df_sector_ts['rank']>5,'iso3_country'] = 'NUL'
                filtered_df_sector_ts.loc[filtered_df_sector_ts['rank']>5,'country'] = 'Rest'

                filtered_df_sector_ts = filtered_df_sector_ts.groupby(['year','country']).emissions_quantity.sum().reset_index()
                filtered_df_sector_ts = filtered_df_sector_ts.loc[filtered_df_sector_ts['year']<=st.session_state.year,:]
                
                category_order = ['Rest'] + [country for country in filtered_df_sector_ts['country'].unique() if country != 'Rest']

                fig_ts_cty_bar = px.bar(
                    filtered_df_sector_ts,
                    x='year', 
                    y='emissions_quantity', 
                    labels={'emissions_quantity': 'Emissions'},
                    title=f'Top Countries in {st.session_state.sector}',
                    text='country',  # Add labels on top of the bars
                    height=st_layout['height_row'],
                    color='country',
                    category_orders={'country': category_order}  # Set the order of categories
                )
                fig_ts_cty_bar.update_layout(showlegend=False)
                fig_ts_cty_bar.update_xaxes(tickangle=-90)
                fig_ts_cty_bar.update_traces(textposition='inside', textfont_size=10, hovertemplate='Country: %{text}<br>Emissions: %{y:.2s}')
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

        if st.session_state.choice == 'all sectors':
            df_yr_treemap = df_yr_treemap.loc[df_yr_treemap['sector'].isin(['forestry-and-land-use'])==False,:]

        with layout_col1:
            filtered_df_country = df_yr_treemap[df_yr_treemap['iso3_country'] == st.session_state.country] if st.session_state.country != 'global' else df_yr_treemap
            fig_country = generate_fig(filtered_df_country, ['sector','subsector'], 'emissions_quantity', None)
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
        df_top10['emissions_total'] = df_top10.groupby(['sector'])['emissions_quantity'].transform('sum')

        df_top10 = df_top10.loc[df_top10['rank']<=10,:]
        df_top10['contents'] = df_top10['country'] + df_top10['emissions_pct'].apply(lambda x: " ({:,.0f}%)".format(x))
        df_top10 = df_top10.pivot_table(index=['sector','emissions_total'], columns='rank',values='contents', aggfunc='first')

        df_top10 = df_top10.sort_values(by='sector', key=lambda x: x == 'all sectors', ascending=False)

        st.dataframe(df_top10, use_container_width=True, height=st_layout['height_row']-50)

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

            st.dataframe(df_top10, use_container_width=True, height=st_layout['height_row']-50)
            st.write("note:  forestry percentage uses positive emissions only")

    with st.container():
        # st.markdown(f"<h2 style='display: inline-block; vertical-align: middle;'>Climate TRACE Emissions Data Pivot Table {st.session_state.year}</h2>", unsafe_allow_html=True)
        st.header("Comprehensive Emissions Table " + str(st.session_state.year))
        
        df_tb = st.session_state.df_yr[['continent_ct','iso3_country','country','sector','subsector','asset_type','emissions_quantity','activity','capacity']]
        df_tb.sort_values(['continent_ct','iso3_country','sector','subsector','asset_type'], inplace=True)
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
        fds_col = ['year']
        fds_val = ['emissions_quantity','count']
        display_fds = fds_col + fds_row + fds_val

        df_tb = st.session_state.df[display_fds]
        df_tb = df_tb.loc[df_tb['year'].isin([st.session_state.year,st.session_state.year1]),:]
        df_tb.rename(columns={'emissions_quantity': 'emissions', 'count': '#assets'}, inplace=True)

        # *** #assets ***
        # fds_val1 = ['emissions','#assets']  
        fds_val1 = ['emissions']                
        df_tb = df_tb.pivot_table(index=fds_row, columns=fds_col, values=fds_val1)
        
        df_tb.columns = ['_'.join([str(x) for x in col]).strip() for col in df_tb.columns]
        df_tb['emissions_' + '-'.join([str(st.session_state.year), str(st.session_state.year1)])] = df_tb['_'.join(["emissions",str(st.session_state.year)])] - df_tb['_'.join(["emissions",str(st.session_state.year1)])]
        # *** #assets ***
        # df_tb['#assets_' + '-'.join([str(st.session_state.year), str(st.session_state.year1)])] = df_tb['_'.join(["#assets",str(st.session_state.year)])] - df_tb['_'.join(["#assets",str(st.session_state.year1)])]
        df_tb.reset_index(inplace=True)

        dict_fds_agg = {'emissions': [
                '_'.join(["emissions",str(st.session_state.year)]),
                '_'.join(["emissions",str(st.session_state.year1)]),
                'emissions_' + '-'.join([str(st.session_state.year), str(st.session_state.year1)])
            ],
            # *** #assets ***
            # '#assets': [
            #     '_'.join(["#assets",str(st.session_state.year)]),
            #     '_'.join(["#assets",str(st.session_state.year1)]),
            #     '#assets_' + '-'.join([str(st.session_state.year), str(st.session_state.year1)]),
            # ]   
        }

        fds_reordered = fds_row 
        for v in dict_fds_agg.values():
            fds_reordered += v

        def js_tb(fds_agg):
            percentage_js = JsCode(f"""
                function(params) {{
                    if (params.node.groupData) {{
                        var value1Field = '{fds_agg[0]}';  // Dynamic column name for Value1
                        var value2Field = '{fds_agg[1]}';  // Dynamic column name for Value2

                        var totalValue1 = params.node.aggData[value1Field] || 0;  // Aggregated data for dynamic column name
                        var totalValue2 = params.node.aggData[value2Field] || 0;  // Aggregated data for dynamic column name

                        if (totalValue2 !== 0) {{
                            return ((totalValue1 / totalValue2 -1)* 100).toFixed(1) + '%';
                        }} else {{
                            return '0%';
                        }}
                    }} else {{
                        return '';
                    }}
                }}
                """)
            return percentage_js

        gb = GridOptionsBuilder.from_dataframe(df_tb[fds_reordered])
        gb.configure_side_bar()  # Add a sidebar for filtering

        gridOptions = gb.build()

        gridOptions['columnDefs'] = [
            {'headerName': 'continent', 'field': 'continent_ct', 'rowGroup': True, 'hide': True},
            {'headerName': 'country', 'field': 'country', 'rowGroup': True, 'showRowGroup': 'country', 'filter': 'agTextColumnFilter'},
            {'headerName': 'sector', 'field': 'sector', 'rowGroup': True, 'showRowGroup': 'sector', 'filter': 'agTextColumnFilter'},
            {'headerName': 'subsector', 'field': 'subsector', 'rowGroup': True, 'showRowGroup': 'subsector', 'filter': 'agTextColumnFilter'},
            {'headerName': 'asset_type', 'field': 'asset_type', 'rowGroup': True, 'showRowGroup': 'asset_type', 'filter': 'agTextColumnFilter'},
        ]

        gridOptions['columnDefs'] += [
            {'headerName': x, 'field': x, 'suppressAggFuncInHeader': True,  'type': ["numericColumn", "customNumericFormat"], 'aggFunc': 'sum', 'precision': 0, 'valueFormatter': "x.toLocaleString('en-US', {minimumFractionDigits: 0, maximumFractionDigits: 0})"}
            for x in dict_fds_agg['emissions']
        ]

        gridOptions['columnDefs'] += [    
            {'headerName': 'emissions_%', 'field': 'emissions_change', 'valueGetter': js_tb(dict_fds_agg['emissions'][:2]), 'cellStyle': {'textAlign': 'right'}, 'headerClass': 'header-align-right'},
        ]

        # *** #assets ***
        # gridOptions['columnDefs'] += [
        #     {'headerName': x, 'field': x, 'suppressAggFuncInHeader': True,  'type': ["numericColumn", "customNumericFormat"], 'aggFunc': 'sum', 'precision': 0, 'valueFormatter': "x.toLocaleString('en-US', {minimumFractionDigits: 0, maximumFractionDigits: 0})"}
        #     for x in dict_fds_agg['#assets']
        # ]

        # gridOptions['columnDefs'] += [    
        #     {'headerName': '#assets_%', 'field': '#assets_change', 'valueGetter': js_tb(dict_fds_agg['#assets'][:2]), 'cellStyle': {'textAlign': 'right'}, 'headerClass': 'header-align-right'},
        # ]

        gridOptions['domLayout'] = 'autoHeight'  # Automatically adjust the grid height
        gridOptions['suppressHorizontalScroll'] = True  # Suppress the horizontal scroll to fit columns to the grid width
        gridOptions['defaultColDef'] = {'flex': 1}  # Set flex grow for columns to auto-size

        df_agGrid = AgGrid(df_tb[fds_reordered], gridOptions=gridOptions, update_mode=GridUpdateMode.NO_UPDATE, enable_enterprise_modules=True, allow_unsafe_jscode=True) #,  fit_columns_on_grid_load=True)

        grid_data = pd.DataFrame(df_agGrid['data'])

        # # Convert the DataFrame to CSV
        # csv = grid_data.to_csv(index=False)

        # # Add a download button above the table
        # st.download_button(
        #     label="Download CSV",
        #     data=csv,
        #     file_name='aggrid_data.csv',
        #     mime='text/csv'
        # )