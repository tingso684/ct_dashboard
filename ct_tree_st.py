import streamlit as st
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
        # # Optimize data types
        # df['sector'] = df['sector'].astype('category')
        # df['subsector'] = df['subsector'].astype('category')
        # df['iso3_country'] = df['iso3_country'].astype('category')
        # df['continent_ct'] = df['continent_ct'].astype('category')
        return df

    df = load_data(os.path.join(csv_directory, selected_file))

    # Formatting function for generating a treemap figure
    def generate_fig(data, path, value, color):
        total_value = data['co2e_100yr'].sum()

        fig = px.treemap(data, path=path, values=value, color=color,
                         title='Treemap for Climate TRACE data')

        fig.update_layout(
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

# import pandas as pd
# import streamlit as st
# import plotly.express as px
# from streamlit_plotly_events import plotly_events

# # Load data
# fname = 'ct_treemap_data.csv'
# df = pd.read_csv(fname)

# # Set page config
# st.set_page_config(layout="wide")

# # Title
# st.title('Interactive Treemap')

# # Initialize session state
# if 'current_path' not in st.session_state:
#     st.session_state.current_path = ['sector', 'subsector']
# if 'df_chart' not in st.session_state:
#     st.session_state.df_chart = df.copy()

# # Define all levels
# all_levels = ['sector', 'subsector', 'iso3_country']

# # Function to update treemap
# def update_treemap(clicked_label):
#     new_path = st.session_state.current_path.copy()
#     df_chart = st.session_state.df_chart.copy()
    
#     if clicked_label:
#         for idx, p in enumerate(all_levels):
#             if clicked_label in df[p].unique():
#                 clicked_level = p
#                 break
        
#         clicked_index = all_levels.index(clicked_level)
#         current_index = all_levels.index(st.session_state.current_path[-1])
        
#         if clicked_index == current_index:
#             if clicked_index == 0:
#                 new_path = all_levels[clicked_index:clicked_index + 2]
#             elif clicked_index == len(all_levels) - 1:
#                 new_path = all_levels[max(0, clicked_index - 1):clicked_index + 1]
#             else:
#                 new_path = all_levels[clicked_index:clicked_index + 2]
#         elif clicked_index < current_index:
#             if clicked_index == 0:
#                 new_path = all_levels[clicked_index:clicked_index + 2]
#             else:
#                 new_path = all_levels[max(0, clicked_index - 1):clicked_index + 1]
#         else:
#             if clicked_index == len(all_levels) - 1:
#                 new_path = all_levels[max(0, clicked_index - 1):clicked_index + 1]
#             else:
#                 new_path = all_levels[clicked_index:clicked_index + 2]
        
#         new_path = new_path[:2]
        
#         if clicked_index == 0:
#             pass
#         elif clicked_index == len(all_levels) - 1:
#             clicked_label_parent = df[df[clicked_level] == clicked_label][new_path[0]].iloc[0]
#             df_chart = df_chart[df_chart[new_path[0]] == clicked_label_parent]
#         else:
#             df_chart = df_chart[df_chart[all_levels[clicked_index]] == clicked_label]
    
#     st.session_state.current_path = new_path
#     st.session_state.df_chart = df_chart

# # Create treemap
# fig = px.treemap(st.session_state.df_chart, path=st.session_state.current_path, values='co2e_100yr', color='continent_ct')

# fig.update_layout(
#     margin=dict(t=0, l=0, b=0, r=0),
#     paper_bgcolor='white',
#     uniformtext_minsize=10,
#     uniformtext_mode='hide',
#     clickmode='event+select'  # Ensure click events are enabled
# )

# fig.update_traces(
#     hovertemplate='%{label}<br>Value: %{value}<br>Percent of Total: %{percent.entry:.2%}',
#     textinfo='label+percent entry+value',
#     textfont_size=10,
#     marker=dict(line=dict(width=0))
# )

# # Display the plot
# st.plotly_chart(fig, use_container_width=True)

# # Capture click events
# selected_points = plotly_events(fig, click_event=True)

# # Process click data
# if selected_points:
#     click_info = selected_points[0]
    
#     # Extract label
#     clicked_label = click_info.get('label')
    
#     if clicked_label:
#         st.write("Clicked Label:", clicked_label)
        
#         # Update treemap based on the clicked label
#         update_treemap(clicked_label)

#         # Display the updated treemap
#         fig = px.treemap(st.session_state.df_chart, path=st.session_state.current_path, values='co2e_100yr', color='continent_ct')
#         st.plotly_chart(fig, use_container_width=True)


# import streamlit as st
# import plotly.express as px
# import pandas as pd
# from streamlit.components.v1 import html

# # Sample DataFrame
# df = pd.DataFrame({
#     "Category": ["A", "B", "C", "A", "B", "C"],
#     "Subcategory": ["X", "X", "X", "Y", "Y", "Y"],
#     "Value": [10, 20, 30, 40, 50, 60]
# })

# # Create a Plotly treemap
# fig = px.treemap(df, path=['Category', 'Subcategory'], values='Value')

# # Convert the figure to JSON
# fig_json = fig.to_json()

# # HTML/JS for Plotly and communication
# clicked_label = st.components.v1.html(f"""
#     <div id="plotly-div"></div>
#     <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
#     <script>
#         var plotly_data = {fig_json};
#         var plotly_div = document.getElementById('plotly-div');
#         Plotly.newPlot(plotly_div, plotly_data.data, plotly_data.layout);

#         plotly_div.on('plotly_click', function(data) {{
#             var clicked_label = data.points[0].label;
#             document.getElementById('click-output').innerText = "You clicked on: " + clicked_label;

#             // Send the clicked label back to Streamlit
#             const message = {{
#                 type: "streamlit:setComponentValue",
#                 value: clicked_label
#             }};
#             window.parent.postMessage(message, "*");
#         }});
#     </script>
#     <div id="click-output">Click on a segment to see the label</div>
# """, height=600)

# # Display the clicked label
# st.write("Last clicked label:", clicked_label)
