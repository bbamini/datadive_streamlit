import streamlit as st
import pandas as pd
import geopandas as gpd
import plotly.express as px
import shapely.geometry
import numpy as np

st.set_page_config(page_title="Southern Africa Buildings Census and Recent Storms")
st.title('Southern Africa Buildings Census')

with st.sidebar:
    st.image('./DataDive_logo.png')

option = st.sidebar.selectbox(
    'Country:',
    ('South Africa', 'Mozambique')
)

st.header(option)

if option == 'South Africa':
    dom_df = pd.read_csv('south_africa_95conf_W1_6.csv')
    dom_df['iso_3'] = 'ZAF'
    f = r"ZAF_adm/ZAF_adm2.shp" #NAME_2 for Magisterial district
    shapes = gpd.read_file(f)
    c_lat = -30.5595
    c_lon = 22.9375
    dom_all = pd.read_csv('southafrica_90conf_dom_height_all.csv.zip', compression="zip")
elif option == 'Mozambique':
    dom_df = pd.read_csv('mozambique_95conf_W1_6.csv')
    dom_df['iso_3'] = 'MOZ'
    f = r"MOZ_adm/MOZ_adm2.shp" #NAME_2 for district
    shapes = gpd.read_file(f)
    shapes.replace({'Zambezia': 'Zambézia', 'Niassa':'Nassa'}, inplace=True)
    c_lat = -18.6657
    c_lon = 35.5296
    dom_all = pd.read_csv('mozambique_90conf_dom_height_all.csv.zip', compression="zip")

dom_df = dom_df[dom_df.Country.notna()]
geodf = gpd.GeoDataFrame(
    dom_df,
    geometry=gpd.points_from_xy(dom_df.longitude, dom_df.latitude),
    crs='EPSG:4326'
    )


st.subheader('Building Locations')

st.markdown('Buildings dataset is pulled from [Google Open Buildings dataset](https://sites.research.google/open-buildings/) and reverse geocoded using [Nominatim API](https://nominatim.org/release-docs/latest/)')

st.markdown('Buildings with confidence at or above 95\% are shown below. Point size correspoinds to building area estimate. Point color corresponds to confidence.')

fig1 = px.scatter_mapbox(geodf,
                        lat="latitude",
                        lon="longitude",
                        hover_name="City",
                        hover_data=["Type", "AddressType", "area_in_meters", "height_net", "vol_2025"],
                        color='confidence',
                        size='area_in_meters',
                        color_continuous_scale = 'sunset',
                        zoom=3,
                        height=300,
                        title = 'Building Locations')
fig1.update_layout(mapbox_style="open-street-map")
fig1.update_layout(margin={"r":0,"t":0,"l":0,"b":0})
st.plotly_chart(fig1, use_container_width=True)

all_90_conf = gpd.sjoin(
    gpd.GeoDataFrame(
        dom_all,
        geometry=gpd.points_from_xy(dom_all.longitude, dom_all.latitude),
        crs='EPSG:4326'
        ),
    shapes,
    op='within'
)

building_density = all_90_conf.dissolve(
     by="NAME_2",
     aggfunc={
         "NAME_0": "count",
         "area_in_meters": "sum",
         "pop_2025":"sum"
     },
 )
building_density.reset_index(inplace=True)
building_density = shapes.merge(building_density[['NAME_2', 'NAME_0', 'area_in_meters', 'pop_2025']], on = "NAME_2")

st.subheader('Building Density by District')

st.markdown('Spatial administrative boundaries data was obtained from [Diva-GIS](http://www.diva-gis.org/gdata)')

st.markdown('The figure below pulls buildings at or above 90\% confidence from Google Open Buildings and joins this with administrative boundaries. The counts of buildings at or above 90\% confidence within each administrative boundary serves to estimate the density.')
st.markdown('Caveat: If certain districts have lower confidence overall due to regional geographic aspects then this map may mislead building density.')

fig0 = px.choropleth(building_density,
                   geojson=building_density.geometry,
                   locations=building_density.index,
                   color='NAME_0_y',
                   hover_name = 'NAME_2',
                   hover_data = 'NAME_1',
                   color_continuous_scale = 'plasma',
                   projection="mercator",
                   labels='Building Density'
                   )
fig0.update_geos(fitbounds="locations", visible=False)
#fig0.show()
st.plotly_chart(fig0, use_container_width=True)

st.subheader('Building Areas')

st.markdown('The figure below pulls buildings at or above 95\% confidence from Google Open Buildings and joins this with administrative boundaries.')
st.markdown('Caveat: If certain districts have lower confidence overall due to regional geographic aspects then this map may mislead building size density.')

fig = px.density_mapbox(geodf,
                        lat = 'latitude',
                        lon = 'longitude',
                        z = 'area_in_meters', 
                        hover_name = 'Type',
                        color_continuous_scale = 'sunset',
                        radius = 8,
                        center = dict(lat = c_lat, lon = c_lon),
                        zoom = 3,
                        labels='Area in m2',
                        mapbox_style = 'open-street-map',
                        title = 'Heatmap of Building Areas'
                        )
fig.update_layout(margin={"r":0,"t":0,"l":0,"b":0})
st.plotly_chart(fig, use_container_width=True)


st.markdown('The figure below pulls buildings at or above 90\% confidence from Google Open Buildings and joins this with administrative boundaries. The colors show the aggregate sum of these building areas within the district. It serves to estimate land area coverage by buildings.')
st.markdown('Caveat: If certain districts have lower confidence overall due to regional geographic aspects then this map may mislead building size density analysis.')


fig2 = px.choropleth(building_density,
                   geojson=building_density.geometry,
                   locations=building_density.index,
                   color='area_in_meters',
                   hover_name = 'NAME_2',
                   hover_data = 'NAME_1',
                   color_continuous_scale = 'plasma',
                   projection="mercator",
                   labels='Building Area Coverage'
                   )
fig2.update_geos(fitbounds="locations", visible=False)
#fig2.show()
st.plotly_chart(fig2, use_container_width=True)

st.subheader('Storm Traces')

st.markdown('The storm dataset is sourced from [IBTrACS v4](https://www.ncei.noaa.gov/products/international-best-track-archive) for the South Indian ocean basin.')
st.markdown('Figure may take several minutes to load. Shown below are storm traces overlaid with buildings above 95\% confidence.')


floods = gpd.read_file('IBTrACS.SI.list.v04r00.lines.zip')

lats = []
lons = []
names = []
times = []

recent_floods = floods[floods['SEASON'] >= 2000]
recent_flood_limited = gpd.sjoin(
    recent_floods,
    shapes,
    op='within'
)

for feature, name, t in zip(recent_flood_limited.geometry, recent_flood_limited.NAME, recent_flood_limited.ISO_TIME):
    if isinstance(feature, shapely.geometry.linestring.LineString):
        linestrings = [feature]
    elif isinstance(feature, shapely.geometry.multilinestring.MultiLineString):
        linestrings = feature.geoms
    else:
        continue
    for linestring in linestrings:
        x, y = linestring.xy
        lats = np.append(lats, y)
        lons = np.append(lons, x)
        names = np.append(names, [name]*len(y))
        times = np.append(times, [t]*len(y))
        lats = np.append(lats, None)
        lons = np.append(lons, None)
        names = np.append(names, None)
        times = np.append(times, None)

fig4 = px.line_mapbox(lat=lats, lon=lons,
                      mapbox_style = 'open-street-map',
                      center = dict(lat = c_lat, lon = c_lon),
                      hover_name=names,
                      color=names,
                      hover_data=[times],
                      zoom=3,
                      color_discrete_sequence=px.colors.sequential.Rainbow_r)
fig4.update_layout(margin={"r":0,"t":0,"l":0,"b":0})
fig5 = px.scatter_mapbox(geodf,
                        lat="latitude",
                        lon="longitude",
                        hover_name="City",
                        hover_data=["Type", "AddressType", "area_in_meters", "height_net", "vol_2025"],
                        size='area_in_meters',
                        zoom=3,
                        height=300,
                        title = 'Building Locations')
fig5.update_layout(mapbox_style="open-street-map")
fig5.update_layout(margin={"r":0,"t":0,"l":0,"b":0})
fig4.add_trace(fig5.data[0])
st.plotly_chart(fig4, use_container_width=True)