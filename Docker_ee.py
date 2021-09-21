#!/usr/bin/env python
# coding: utf-8

# # Access to Google Earth Engine (GEE) objects and methods 

# In[24]:


import ee


# In[25]:


#For authentifications we require a Google Account registered in GEE (https://earthengine.google.com/)
ee.Authenticate()


# In[26]:


ee.Initialize()


# # Define input data 

# In[27]:


#Initial date of interest(inclusive)and final date of interest (exclusive)
start = '2017-03-28'                                     #First S2 L2A image date
#start = '2020-09-01'   
end   = '2021-12-31'                                     #2017-05-12 starts frequency of 10 days
                                                         #2017-12-18 starts frequency of 5 days
time  = [start, end]


# In[28]:


#Region of interest(coordinates + buffer)     
lon_lat         =  [-6.434, 36.998]         #Duque Fuente EC coordiantes
projection_EPSG =  'EPSG:4326'              

point = ee.Geometry.Point(lon_lat,projection_EPSG)
type(point)


# In[29]:


#Region of interest(polygon)                
geometry   = [[-6.440, 37.222],
              [-6.440, 36.835],
              [-5.878, 36.835],
              [-5.878, 37.222]]

region     = ee.Geometry.Polygon([geometry])
type(region)


# In[30]:


#Region of interest(shape file) 

shapefile  = ee.FeatureCollection("users/mafmonjaraz/DNP_limits")
region_shp = shapefile.geometry()
type(region_shp)


# In[31]:


#Data set catalogs used in this code
#data_info = ['id','longitude','latitude','time'] //Constant bands. Time measured in miliseconds since 1970
COPERNICUS_S2_L2A = 'COPERNICUS/S2_SR'                   #Multi-spectral surface reflectances (https://developers.google.com/earth-engine/datasets/catalog/COPERNICUS_S2_SR)
COPERNICUS_S2_bands = ['B1', 'B2', 'B3', 'B4', 'B5', 'B6', 'B7', 'B8', 'B8A', 'B9', 'B11', 'B12', 'AOT', 'WVP', 'SCL', 'TCI_R', 'TCI_G', 'TCI_B', 'QA10', 'QA20', 'QA60']
MODIS_temp = 'MODIS/006/MOD11A1'                         #Land surface temperature (https://developers.google.com/earth-engine/datasets/catalog/MODIS_006_MOD11A1)
MODIS_temp_bands  = ['LST_Day_1km','QC_Day','Day_view_time','Day_view_angle','LST_Night_1km','QC_Night','Night_view_time','Night_view_angle','Emis_31','Emis_32','Clear_day_cov','Clear_night_cov']
USAID_prec = 'UCSB-CHG/CHIRPS/DAILY'                     #InfraRed Precipitation with Station dat (https://developers.google.com/earth-engine/datasets/catalog/UCSB-CHG_CHIRPS_DAILY)
USAID_prec_bands  = ['precipitation']
MODIS_GPP = 'MODIS/006/MOD17A2H'                         #Gross primary productivity(https://developers.google.com/earth-engine/datasets/catalog/MODIS_006_MOD17A2H)
MODIS_GPP_bands = ['Gpp', 'PsnNet', 'Psn_QC']
MODIS_NPP = 'MODIS/006/MOD17A3HGF'                       #Net primary productivity (https://developers.google.com/earth-engine/datasets/catalog/MODIS_006_MOD17A3HGF)
MODIS_NPP_bands = ['Npp', 'Npp_QC']

#image.bandNames() can be used to request bands of colections as well


# # Load data sets of interes

# In[32]:


#Function to load data set with specified period and location
def load_catalog(catalog, time, location, bands):
    dataset = ee.ImageCollection(catalog).filterDate(time[0],time[1]).filterBounds(location).select(bands)
    return dataset


# In[33]:


#Request of catalogues 
S2     = load_catalog(COPERNICUS_S2_L2A, time, point, COPERNICUS_S2_bands)
temp   = load_catalog(MODIS_temp,        time, point, MODIS_temp_bands)
prec   = load_catalog(USAID_prec,        time, point, USAID_prec_bands)
gpp    = load_catalog(MODIS_GPP,         time, point, MODIS_GPP_bands)
npp    = load_catalog(MODIS_NPP,         time, point,  MODIS_NPP_bands)


# # Cloud coverage image filter

# In[34]:


cloud_coverage_metadata_name = 'CLOUDY_PIXEL_PERCENTAGE'           #Name of metadata property indicating cloud coverage in %
max_cloud_coverage = 100                                          #Maximun cloud coverage allowed

#Cloud coverage filter function (cf)
def cloud_filter(collection, cloud_coverage_metadata_name, threshold = 100):
    collection_cf = collection.filterMetadata(cloud_coverage_metadata_name,'less_than', threshold)
    return collection_cf

#Applying filter
S2_cloud_filter = cloud_filter(S2, cloud_coverage_metadata_name, max_cloud_coverage)


# # Calculate Vegetation Indices

# In[35]:


#Defining dictionary of bands 

dict_bands = {
    "blue"  :  'B2',                              #Blue band                        
    "green" :  'B3',                              #Green band
    "red"   :  'B4',                              #Red band
    "red2"  :  'B6',                              #Red-edge spectral band
    "NIR"   :  'B8',                              #Near-infrared band
    "SWIR1" :  'B11',                             #Short wave infrared 1
    "SWIR2" :  'B12',                             #Short wave infrared 2
}


# In[36]:


def calculateVI(image):
    '''This method calculates different vegetation indices in a image collection and adds their values as new bands'''

    #Specify bands 
    dict  = dict_bands
    blue  = dict["blue"]                          #Blue band                        
    green = dict["green"]                         #Green band
    red   = dict["red"]                           #Red band
    red2  = dict["red2"]                          #Red-edge spectral band
    NIR   = dict["NIR"]                           #Near-infrared band
    SWIR1 = dict["SWIR1"]                         #Short wave infrared 1
    SWIR2 = dict["SWIR2"]                         #Short wave infrared 2
    
    bands_for_expressions = {
        'blue'  : image.select(blue).divide(10000),
        'green' : image.select(green).divide(10000), 
        'red'   : image.select(red).divide(10000),
        'red2'  : image.select(red2).divide(10000), 
        'NIR'   : image.select(NIR).divide(10000),
        'red'   : image.select(red).divide(10000), 
        'SWIR1' : image.select(SWIR1).divide(10000),
        'SWIR2' : image.select(SWIR2).divide(10000)}
    
    #NDVI                                                                            (Rouse et al., 1974)
    ndvi  = image.normalizedDifference([NIR, red]).rename("ndvi") 
    #GNDVI                                                                           (Add reference)
    gndvi = image.normalizedDifference([NIR, green]).rename("gndvi")
    #NDWI                                                                            (Add reference)
    ndwi  = image.normalizedDifference([NIR, SWIR2]).rename("ndwi")
    #EVI                                                                             (Add reference)
    evi   = image.expression('2.5*(( NIR - red ) / ( NIR + 6 * red - 7.5 * blue +1 ))', bands_for_expressions).rename("evi")
    #EVI2                                                                            (Jiang et al., 2008)
    evi2  = image.expression('2.5*(( NIR - red ) / ( NIR + 2.4 * red+1 ))', 
            bands_for_expressions).rename("evi2");
    
    #Other indeces sensitive to above ground biomas/carbon 
    #(https://webapps.itc.utwente.nl/librarywww/papers_2017/msc/nrm/adan.pdf)
    
    #RENDVI                                                                          (Chen et al. 2007)
    rendvi = image.normalizedDifference([NIR, red2]).rename("rendvi")
    #NDII                                                                            (Hunt & Qu, 2013)
    ndii   = image.normalizedDifference([NIR, SWIR1]).rename("ndii")
    #RERVI                                                                           (Cao et al., 2016)
    rervi  = image.expression('NIR / red2', bands_for_expressions).rename("rervi");
    #RE-EVI2                                                                         (Abdel-rahman et al., 2017)
    revi2  = image.expression('2.5*(( NIR - red2 ) / ( NIR + 2.4 * red2 +1 ))', bands_for_expressions).rename("revi2");
    
    image1 = image.addBands(ndvi).addBands(gndvi).addBands(ndwi)
    image2 = image1.addBands(evi).addBands(evi2).addBands(rendvi)
    image3 = image2.addBands(ndii).addBands(rervi).addBands(revi2)
    
    return image3


# In[37]:


#Calculation of vegetation indices for the collection
S2_VI = S2_cloud_filter.map(calculateVI)


# # Cut images to the Country Limits

# In[38]:


country = 'Spain'
#countries_shp = ee.FeatureCollection('FAO/GAUL/2015/level0').select('ADM0_NAME')
#country_shp = countries_shp.filter(ee.Filter.eq('ADM0_NAME', country))
#clip = country_shp


# In[39]:


def clipToCountry(image,country):
    countries_shp = ee.FeatureCollection('FAO/GAUL/2015/level0').select('ADM0_NAME')
    country_shp = countries_shp.filter(ee.Filter.eq('ADM0_NAME', country))
    clip = country_shp
    
    def clipToShp(image_fun):
        clipped = image_fun.clip(clip)
        return clipped
    
    country_clip = image.map(clipToShp)
    return country_clip


# In[40]:


S2_VI_clip_country = clipToCountry(S2_VI,country)


# # Cut images to the National Park Limits 

# In[41]:


clip = region_shp


# In[42]:


def clipToRegion(image,region):
    clip = region
    def clipToShp(image_fun):
        clipped = image_fun.clip(clip)
        return clipped
    region_clip = image.map(clipToShp)
    return region_clip


# In[43]:


S2_VI_clip = clipToRegion(S2_VI_clip_country,clip)
temp_clip  = clipToRegion(temp,clip)
prec_clip  = clipToRegion(prec,clip)


# # Display maps

# In[46]:


#get_ipython().system(' pip install folium')


# In[47]:


import folium


# In[48]:


#Select images
ima_NDVI = S2_VI_clip.select('ndvi').mean()                                     #Maximun NDVI in the perido "time" 
ima_Temp = temp_clip .select('LST_Day_1km').mean().multiply(0.02).add(-273.15) #Mean temperature in the period "time"
ima_Prec = prec_clip.select('precipitation').mean()                            #Mean precipitation in the period "time"

#Set visualization parameters 
visNDVI = {"min":0, "max":0.75 ,"palette":["ff4545","fbffbe","a7ff7a","009356","1f1e6e"]}
visTemp = {'min': 0, 'max': 40,'palette': ['white', 'blue', 'green', 'yellow', 'orange', 'red']}
visPrec = {'min': 0, 'max': 30,'palette': ['white', 'blue', 'gray', 'purple']}


# Arrange layers inside a list 
ee_tiles = [ima_Prec, ima_Temp, ima_NDVI]

# Arrange visualization parameters inside a list.
ee_vis_params = [visPrec, visTemp, visNDVI]

# Arrange layer names inside a list.
ee_tiles_names = ['Precipitation','Land Surface Temperature','NDVI',]


# In[49]:


#Function to add layers to the map
def add_ee_layer(self, ee_image_object, vis_params, name):
    """Adds a method for displaying Earth Engine image tiles to folium map."""
    map_id_dict = ee.Image(ee_image_object).getMapId(vis_params)
    folium.raster_layers.TileLayer(
        tiles=map_id_dict['tile_fetcher'].url_format,
        attr='Map Data &copy; <a href="https://earthengine.google.com/">Google Earth Engine</a>',
        name=name,
        overlay=True,
        control=True
    ).add_to(self)

# Add Earth Engine drawing method to folium.
folium.Map.add_ee_layer = add_ee_layer


# In[50]:


# Create a  map.
map_variables = folium.Map(location= [lon_lat[1], lon_lat[0]], zoom_start=12)

# Add layers to the map using a loop.
for tile, vis_param, name in zip(ee_tiles, ee_vis_params, ee_tiles_names):
    map_variables.add_ee_layer(tile, vis_param, name)

folium.LayerControl(collapsed = False).add_to(map_variables)

# Display the map.
#display(map_variables)


# # Save map in html format

# In[51]:


#Save map in html
map_variables.save('DNP_indices.html')

