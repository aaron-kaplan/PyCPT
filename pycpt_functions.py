#This is PyCPT_functions.py (version1.2) -- 6 June 2019
#Authors: AG Muñoz (agmunoz@iri.columbia.edu) and AW Robertson (awr@iri.columbia.edu)
#Notes: be sure it matches version of PyCPT
#Log:

# 6 June 2019, AGM: fixed bug in PyIngrid related to the number of initializations used
#					for the ECMWF model, and optimized reading multiple records in
#					sequential Fortran binary (GrADS) files.
# 21 Apr 2019, AGM: added option to list average skill metrics for particular subdomains.
# 17 Apr 2019, AGM: fixed bug related to the inverse Gamma function.
#30 Mar 2019, AGM: added PCR option, CHIRPS as obs, flexible format plots,
#					automatically uses retrospective for validation (due to
#					the very high sample size). Solved problems related to
#					masking missing values. ELR still has some problems
#					(values are different from our R or Matlab codes -- working
#					on it, so not included in this version).
#25 Aug 2018, AGM: plots are now raster maps, added CPC obs,
#				   fixed field shift due to sequential grads format in CPT,
#				   automatic colobar limits and field name for deterministic forecast
#24 Aug 2018, AWR: "obs_source" added for obs dataset selection (passed from main program)
#19 Aug 2018, AWR: Dictionary entry for GEFS added
#To Do: (as March 30th, 2019 -- AGM)
#	+ ELR proceedure is not reproducing results obtained in R or Matlab
#	+ Provide skill stats for user-defined regions
#	+ Simplify download functions: just one function, with the right arguments and dictionaries.
#	+ Check Hindcasts and Forecast_RFREQ
import os
import warnings
import struct
import xarray as xr
import numpy as np
import pandas as pd
from copy import copy
from scipy.stats import t
from scipy.stats import invgamma
import cartopy.crs as ccrs
from cartopy import feature
import matplotlib.pyplot as plt
import matplotlib.colors as colors
from matplotlib.colors import LinearSegmentedColormap
from cartopy.mpl.gridliner import LONGITUDE_FORMATTER, LATITUDE_FORMATTER


warnings.filterwarnings("ignore")

def lines_that_equal(line_to_match, fp):
	return [line for line in fp if line == line_to_match]

def lines_that_contain(string, fp):
	return [line for line in fp if string in line]

def lines_that_start_with(string, fp):
	return [line for line in fp if line.startswith(string)]

def lines_that_end_with(string, fp):
	return [line for line in fp if line.endswith(string)]

def exceedprob(x,dof,lo,sc):
	return t.sf(x, dof, loc=lo, scale=sc)*100

class MidpointNormalize(colors.Normalize):
    def __init__(self, vmin=None, vmax=None, midpoint=None, clip=False):
        self.midpoint = midpoint
        colors.Normalize.__init__(self, vmin, vmax, clip)

    def __call__(self, value, clip=None):
        # I'm ignoring masked values and all kinds of edge cases to make a
        # simple example...
        x, y = [self.vmin, self.midpoint, self.vmax], [0, 0.5, 1]
        return np.ma.masked_array(np.interp(value, x, y))

def download_data(url, authkey, outfile, force_download=False):
	"""A smart function to download data from IRI Data Library
	If the data can be read in and force_download is False, will read from file
	Otherwise will download from IRIDL and then read from file
	Written by J Doss-Gollin (2018)

	PARAMETERS
	----------
		url: the url pointing to the data.nc file
		authkey: the authentication key for IRI DL (see above)
		outfile: the data filename
		force_download: False if it's OK to read from file, True if data *must* be re-downloaded
	"""

	if not force_download:
		try:
			model = xr.open_dataset(outfile, decode_times=False)
		except:
			force_download = True

	if force_download:
		# calls curl to download data
		command = "curl -C - -k -b '__dlauth_id={}' '{}' > {}".format(authkey, url, outfile)
		get_ipython().system(command)
		# open the data
		model = xr.open_dataset(outfile, decode_times=False)

	return model

def PrepFiles(rainfall_frequency, threshold_pctle, wlo1, wlo2,elo1, elo2,sla1, sla2,nla1, nla2, day1, day2, fday, nday, fyr, mon, os, authkey, wk, wetday_threshold, nlag, training_season, hstep, model, obs_source, hdate_last, force_download):
	"""Function to download (or not) the needed files"""
	if rainfall_frequency:
		GetObs_RFREQ(day1, day2, mon, fyr, wlo2, elo2, sla2, nla2, nday, authkey, wk, wetday_threshold, threshold_pctle, nlag, training_season, hstep, model, obs_source, force_download)
		print('Obs:rfreq file ready to go')
		print('----------------------------------------------')
#		nday added after nlag for GEFS & CFSv2
		GetHindcasts(wlo1, elo1, sla1, nla1, day1, day2, fyr, mon, os, authkey, wk, nlag, nday, training_season, hstep, model, hdate_last, force_download)
		#GetHindcasts_RFREQ(wlo1, elo1, sla1, nla1, day1, day2, nday, fyr, mon, os, authkey, wk, wetday_threshold, nlag, training_season, hstep, model, force_download)
		print('Hindcasts file ready to go')
		print('----------------------------------------------')
		#GetForecast_RFREQ(day1, day2, fday, mon, fyr, nday, wlo1, elo1, sla1, nla1, authkey, wk, wetday_threshold, nlag, model, force_download)
		GetForecast(day1, day2, fday, mon, fyr, nday, wlo1, elo1, sla1, nla1, authkey, wk, nlag, model, force_download)
		print('Forecasts file ready to go')
		print('----------------------------------------------')
	else:
		#GetHindcasts(wlo1, elo1, sla1, nla1, day1, day2, fyr, mon, os, authkey, wk, nlag, training_season, hstep, model, force_download)
		#nday added after nlag for GEFS & CFSv2
		GetHindcasts(wlo1, elo1, sla1, nla1, day1, day2, fyr, mon, os, authkey, wk, nlag, nday, training_season, hstep, model, hdate_last, force_download)
		print('Hindcasts file ready to go')
		print('----------------------------------------------')
		GetObs(day1, day2, mon, fyr, wlo2, elo2, sla2, nla2, nday, authkey, wk, nlag, training_season, hstep, model, obs_source, hdate_last, force_download)
		print('Obs:precip file ready to go')
		print('----------------------------------------------')
		GetForecast(day1, day2, fday, mon, fyr, nday, wlo1, elo1, sla1, nla1, authkey, wk, nlag, model, force_download)
		print('Forecasts file ready to go')
		print('----------------------------------------------')

def pltdomain(loni1,lone1,lati1,late1,loni2,lone2,lati2,late2):
	"""A simple plot function for the geographical domain

	PARAMETERS
	----------
		loni: western longitude
		lone: eastern longitude
		lati: southern latitude
		late: northern latitude
		title: title
	"""
	#Create a feature for States/Admin 1 regions at 1:10m from Natural Earth
	states_provinces = feature.NaturalEarthFeature(
		category='cultural',
		name='admin_1_states_provinces_shp',
		scale='10m',
		facecolor='none')

	fig = plt.subplots(figsize=(15,15), subplot_kw=dict(projection=ccrs.PlateCarree()))
	loni = [loni1,loni2]
	lati = [lati1,lati2]
	lone = [lone1,lone2]
	late = [late1,late2]
	title = ['Predictor', 'Predictand']

	for i in range(2):

		ax = plt.subplot(1, 2, i+1, projection=ccrs.PlateCarree())
		ax.set_extent([loni[i],lone[i],lati[i],late[i]], ccrs.PlateCarree())

		# Put a background image on for nice sea rendering.
		ax.stock_img()

		ax.add_feature(feature.LAND)
		ax.add_feature(feature.COASTLINE)
		ax.set_title(title[i]+" domain")
		pl=ax.gridlines(crs=ccrs.PlateCarree(), draw_labels=True,
				  linewidth=2, color='gray', alpha=0.5, linestyle='--')
		pl.xlabels_top = False
		pl.ylabels_left = False
		pl.xformatter = LONGITUDE_FORMATTER
		pl.yformatter = LATITUDE_FORMATTER
		ax.add_feature(states_provinces, edgecolor='gray')
	plt.show()

def pltmap(score,loni,lone,lati,late,fprefix,mpref,training_season, mon, fday, nwk):
	"""A simple function for ploting the statistical score

	PARAMETERS
	----------
		score: the score
		loni: western longitude
		lone: eastern longitude
		lati: southern latitude
		late: northern latitude
		title: title
	"""

	plt.figure(figsize=(20,5))

	for L in range(nwk):
		wk=L+1
		#Read grads binary file size H, W  --it assumes all files have the same size, and that 2AFC exists
		with open('../output/'+fprefix+'_'+mpref+'_2AFC_'+training_season+'_wk'+str(wk)+'.ctl', "r") as fp:
			for line in lines_that_contain("XDEF", fp):
				W = int(line.split()[1])
				XD= float(line.split()[4])
		with open('../output/'+fprefix+'_'+mpref+'_2AFC_'+training_season+'_wk'+str(wk)+'.ctl', "r") as fp:
			for line in lines_that_contain("YDEF", fp):
				H = int(line.split()[1])
				YD= float(line.split()[4])

#		ax = plt.subplot(nwk/2, 2, wk, projection=ccrs.PlateCarree())
		ax = plt.subplot(1,nwk, wk, projection=ccrs.PlateCarree())
		ax.set_extent([loni,loni+W*XD,lati,lati+H*YD], ccrs.PlateCarree())

		#Create a feature for States/Admin 1 regions at 1:10m from Natural Earth
		states_provinces = feature.NaturalEarthFeature(
			category='cultural',
#			name='admin_1_states_provinces_shp',
			name='admin_0_countries',
			scale='10m',
			facecolor='none')

		ax.add_feature(feature.LAND)
		ax.add_feature(feature.COASTLINE)
		ax.set_title(score+' for Week '+str(wk))
		pl=ax.gridlines(crs=ccrs.PlateCarree(), draw_labels=True,
				  linewidth=2, color='gray', alpha=0., linestyle='--')
		pl.xlabels_top = False
		pl.ylabels_left = True
		pl.ylabels_right = False
		pl.xformatter = LONGITUDE_FORMATTER
		pl.yformatter = LATITUDE_FORMATTER
		ax.add_feature(states_provinces, edgecolor='gray')
		ax.set_ybound(lower=lati, upper=late)

		if score == 'CCAFCST_V' or score == 'PCRFCST_V':
			f=open('../output/'+fprefix+'_'+score+'_'+training_season+'_'+mon+str(fday)+'_wk'+str(wk)+'.dat','rb')
			recl=struct.unpack('i',f.read(4))[0]
			numval=int(recl/np.dtype('float32').itemsize)
			#Now we read the field
			A=np.fromfile(f,dtype='float32',count=numval)
			var = np.transpose(A.reshape((W, H), order='F'))
			var[var==-999.]=np.nan #only sensible values
			current_cmap = plt.cm.BrBG
			current_cmap.set_bad('white',1.0)
			current_cmap.set_under('white', 1.0)
			CS=plt.pcolormesh(np.linspace(loni, loni+W*XD,num=W), np.linspace(lati+H*YD, lati, num=H), var,
				#vmin=-max(np.max(var),np.abs(np.min(var))), #vmax=np.max(var),
				norm=MidpointNormalize(midpoint=0.),
				cmap=current_cmap,
				transform=ccrs.PlateCarree())
			ax.set_title("Deterministic forecast for Week "+str(wk))
			if fprefix == 'RFREQ':
				label ='Freq Rainy Days (days)'
			elif fprefix == 'PRCP':
				label = 'Rainfall anomaly (mm/week)'
			f.close()
			#current_cmap = plt.cm.get_cmap()
			#current_cmap.set_bad(color='white')
			#current_cmap.set_under('white', 1.0)
		else:
			#Since CPT writes grads files in sequential format, we need to excise the 4 bytes between records (recl)
			f=open('../output/'+fprefix+'_'+mpref+'_'+score+'_'+training_season+'_wk'+str(wk)+'.dat','rb')
			recl=struct.unpack('i',f.read(4))[0]
			numval=int(recl/np.dtype('float32').itemsize)
			#Now we read the field
			A=np.fromfile(f,dtype='float32',count=numval)
			var = np.transpose(A.reshape((W, H), order='F'))
			#define colorbars, depending on each score	--This can be easily written as a function
			if score == '2AFC':
				var[var<0]=np.nan #only positive values
				CS=plt.pcolormesh(np.linspace(loni, loni+W*XD,num=W), np.linspace(lati+H*YD, lati, num=H), var,
				vmin=0,vmax=100,
				cmap=plt.cm.bwr,
				transform=ccrs.PlateCarree())
				label = '2AFC (%)'

			if score == 'RocAbove' or score=='RocBelow':
				var[var<0]=np.nan #only positive values
				CS=plt.pcolormesh(np.linspace(loni, loni+W*XD,num=W), np.linspace(lati+H*YD, lati, num=H), var,
				vmin=0,vmax=1,
				cmap=plt.cm.bwr,
				transform=ccrs.PlateCarree())
				label = 'ROC area'

			if score == 'Spearman' or score=='Pearson':
				var[var<-1.]=np.nan #only sensible values
				CS=plt.pcolormesh(np.linspace(loni, loni+W*XD,num=W), np.linspace(lati+H*YD, lati, num=H), var,
				vmin=-1,vmax=1,
				cmap=plt.cm.bwr,
				transform=ccrs.PlateCarree())
				label = 'Correlation'

		plt.subplots_adjust(hspace=0)
		#plt.setp([a.get_xticklabels() for a in fig.axes[:-1]], visible=False)
		#cbar_ax = plt.add_axes([0.85, 0.15, 0.05, 0.7])
		#plt.tight_layout()
		plt.subplots_adjust(bottom=0.15, top=0.9)
		cax = plt.axes([0.2, 0.08, 0.6, 0.04])
		cbar = plt.colorbar(CS,cax=cax, orientation='horizontal')
		cbar.set_label(label) #, rotation=270)
		f.close()

def skilltab(score,wknam,lon1,lat1,lat2,lon2,loni,lone,lati,late,fprefix,mpref,training_season,mon,fday,nwk):
	"""A simple function for ploting probabilities of exceedance and PDFs (for a given threshold)

	PARAMETERS
	----------
		thrs: the threshold, in the units of the predictand
		lon: longitude
		lat: latitude
	"""

	#Read grads binary file size H, W  --it assumes all files have the same size, and that 2AFC exists
	with open('../output/'+fprefix+'_'+mpref+'_2AFC_'+training_season+'_wk1.ctl', "r") as fp:
		for line in lines_that_contain("XDEF", fp):
			W = int(line.split()[1])
			XD= float(line.split()[4])
	with open('../output/'+fprefix+'_'+mpref+'_2AFC_'+training_season+'_wk1.ctl', "r") as fp:
		for line in lines_that_contain("YDEF", fp):
			H = int(line.split()[1])
			YD= float(line.split()[4])

	#Find the gridbox:
	lonrange = np.linspace(loni, loni+W*XD,num=W)
	latrange = np.linspace(lati+H*YD, lati, num=H)  #need to reverse the latitudes because of CPT (GrADS YREV option)
	lon_grid, lat_grid = np.meshgrid(lonrange, latrange)
	#first point
	a = abs(lat_grid-lat1)+abs(lon_grid-lon1)
	i1,j1 = np.unravel_index(a.argmin(),a.shape)   #i:latitude   j:longitude
	#second point
	a = abs(lat_grid-lat2)+abs(lon_grid-lon2)
	i2,j2 = np.unravel_index(a.argmin(),a.shape)   #i:latitude   j:longitude

	df = pd.DataFrame(index=wknam[0:nwk])
	for L in range(nwk):
		wk=L+1
		for S in score:
			#Since CPT writes grads files in sequential format, we need to excise the 4 bytes between records (recl)
			f=open('../output/'+fprefix+'_'+mpref+'_'+str(S)+'_'+training_season+'_wk'+str(wk)+'.dat','rb')
			recl=struct.unpack('i',f.read(4))[0]
			numval=int(recl/np.dtype('float32').itemsize)
			#Now we read the field
			A=np.fromfile(f,dtype='float32',count=numval)
			var = np.transpose(A.reshape((W, H), order='F'))
			var[var==-999.]=np.nan #only sensible values
			df.at[wknam[L], str(S)] = round(np.nanmean(np.nanmean(var[i1:i2,j1:j2], axis=1), axis=0),2)
			df.at[wknam[L], 'max('+str(S)+')']  = round(np.nanmax(var[i1:i2,j1:j2]),2)
			df.at[wknam[L], 'min('+str(S)+')']  = round(np.nanmin(var[i1:i2,j1:j2]),2)
	return df
	f.close()

def pltmapProb(loni,lone,lati,late,fprefix,mpref,training_season, mon, fday, nwk):
	"""A simple function for ploting probabilistic forecasts

	PARAMETERS
	----------
		score: the score
		loni: western longitude
		lone: eastern longitude
		lati: southern latitude
		late: northern latitude
		title: title
	"""
	#Need this score to be defined by the calibration method!!!
	score = 'CCAFCST_P'

	plt.figure(figsize=(15,20))

	for L in range(nwk):
		wk=L+1
		#Read grads binary file size H, W  --it assumes that 2AFC file exists (template for final domain size)
		with open('../output/'+fprefix+'_'+mpref+'_2AFC_'+training_season+'_wk'+str(wk)+'.ctl', "r") as fp:
			for line in lines_that_contain("XDEF", fp):
				W = int(line.split()[1])
				XD= float(line.split()[4])
		with open('../output/'+fprefix+'_'+mpref+'_2AFC_'+training_season+'_wk'+str(wk)+'.ctl', "r") as fp:
			for line in lines_that_contain("YDEF", fp):
				H = int(line.split()[1])
				YD= float(line.split()[4])

		#Prepare to read grads binary file  [float32 for Fortran sequential binary files]
		Record = np.dtype(('float32', H*W))

		#Create a feature for States/Admin 1 regions at 1:10m from Natural Earth
		states_provinces = feature.NaturalEarthFeature(
			category='cultural',
#			name='admin_1_states_provinces_shp',
			name='admin_0_countries',
			scale='10m',
			facecolor='none')


		#B = np.fromfile('../output/'+fprefix+'_'+score+'_'+training_season+'_'+mon+str(fday)+'_wk'+str(wk)+'.dat',dtype=Record, count=-1).astype('float')
		f=open('../output/'+fprefix+'_'+score+'_'+training_season+'_'+mon+str(fday)+'_wk'+str(wk)+'.dat','rb')

		tit=['Below Normal','Normal','Above Normal']
		for i in range(3):
				#Since CPT writes grads files in sequential format, we need to excise the 4 bytes between records (recl)
				recl=struct.unpack('i',f.read(4))[0]
				numval=int(recl/np.dtype('float32').itemsize)
				#We now read the field for that record (probabilistic files have 3 records: below, normal and above)
				B=np.fromfile(f,dtype='float32',count=numval) #astype('float')
				endrec=struct.unpack('i',f.read(4))[0]
				var = np.flip(np.transpose(B.reshape((W, H), order='F')),0)
				var[var<0]=np.nan #only positive values
				ax2=plt.subplot(nwk, 3, (L*3)+(i+1),projection=ccrs.PlateCarree())
				ax2.set_title("Week "+str(wk)+ ": "+tit[i])
				ax2.add_feature(feature.LAND)
				ax2.add_feature(feature.COASTLINE)
				#ax2.set_ybound(lower=lati, upper=late)
				pl2=ax2.gridlines(crs=ccrs.PlateCarree(), draw_labels=True,
					linewidth=2, color='gray', alpha=0.5, linestyle='--')
				pl2.xlabels_top = False
				pl2.ylabels_left = True
				pl2.ylabels_right = False
				pl2.xformatter = LONGITUDE_FORMATTER
				pl2.yformatter = LATITUDE_FORMATTER
				ax2.add_feature(states_provinces, edgecolor='gray')
				ax2.set_extent([loni,loni+W*XD,lati,lati+H*YD], ccrs.PlateCarree())

				#ax2.set_ybound(lower=lati, upper=late)
				#ax2.set_xbound(lower=loni, upper=lone)
				#ax2.set_adjustable('box')
				#ax2.set_aspect('auto',adjustable='datalim',anchor='C')
				CS=ax2.pcolormesh(np.linspace(loni, loni+W*XD,num=W), np.linspace(lati,lati+H*YD, num=H), var,
				vmin=0,vmax=100,
				cmap=plt.cm.bwr,
				transform=ccrs.PlateCarree())
				#plt.show(block=False)

	plt.subplots_adjust(hspace=0)
	plt.subplots_adjust(bottom=0.15, top=0.9)
	cax = plt.axes([0.2, 0.08, 0.6, 0.04])
	cbar = plt.colorbar(CS,cax=cax, orientation='horizontal')
	cbar.set_label('Probability (%)') #, rotation=270)
	f.close()

def pltmapff(thrs,ntrain,loni,lone,lati,late,fprefix,mpref,training_season,mon,fday,nwk):
	"""A simple function for ploting probabilistic forecasts in flexible format (for a given threshold)

	PARAMETERS
	----------
		thrs: the threshold, in the units of the predictand
		loni: western longitude
		lone: eastern longitude
		lati: southern latitude
		late: northern latitude
	"""
	#Implement: read degrees of freedom from CPT file
	#Formally, for CCA, dof=ntrain - #CCAmodes -1 ; since ntrain is huge after concat, dof~=ntrain for now
	dof=ntrain

	#Read grads binary file size H, W  --it assumes all files have the same size, and that 2AFC exists
	with open('../output/'+fprefix+'_'+mpref+'_2AFC_'+training_season+'_wk1.ctl', "r") as fp:
		for line in lines_that_contain("XDEF", fp):
			W = int(line.split()[1])
			XD= float(line.split()[4])
	with open('../output/'+fprefix+'_'+mpref+'_2AFC_'+training_season+'_wk1.ctl', "r") as fp:
		for line in lines_that_contain("YDEF", fp):
			H = int(line.split()[1])
			YD= float(line.split()[4])

	plt.figure(figsize=(15,15))

	for L in range(nwk):
		wk=L+1
		#Read mean
		#Since CPT writes grads files in sequential format, we need to excise the 4 bytes between records (recl)
		f=open('../output/'+fprefix+'_'+mpref+'FCST_mu_'+training_season+'_'+str(mon)+str(fday)+'_wk'+str(wk)+'.dat','rb')
		recl=struct.unpack('i',f.read(4))[0]
		numval=int(recl/np.dtype('float32').itemsize)
		#Now we read the field
		A=np.fromfile(f,dtype='float32',count=numval)
		muf = np.transpose(A.reshape((W, H), order='F'))
		muf[muf==-999.]=np.nan #only sensible values

		#Read variance
		f=open('../output/'+fprefix+'_'+mpref+'FCST_var_'+training_season+'_'+str(mon)+str(fday)+'_wk'+str(wk)+'.dat','rb')
		recl=struct.unpack('i',f.read(4))[0]
		numval=int(recl/np.dtype('float32').itemsize)
		#Now we read the field
		A=np.fromfile(f,dtype='float32',count=numval)
		vari = np.transpose(A.reshape((W, H), order='F'))
		vari[vari<0.]=np.nan #only positive values

		#Compute scale parameter for the t-Student distribution
		scalef=np.sqrt((dof-2)/dof*vari)

		fprob = exceedprob(thrs,dof,muf,scalef)

		ax = plt.subplot(nwk/2, 2, wk, projection=ccrs.PlateCarree())
		ax.set_extent([loni,loni+W*XD,lati,lati+H*YD], ccrs.PlateCarree())

		#Create a feature for States/Admin 1 regions at 1:10m from Natural Earth
		states_provinces = feature.NaturalEarthFeature(
			category='cultural',
#			name='admin_1_states_provinces_shp',
			name='admin_0_countries',
			scale='10m',
			facecolor='none')

		ax.add_feature(feature.LAND)
		ax.add_feature(feature.COASTLINE)
		ax.set_title('Probability (%) of Exceeding '+str(thrs)+" mm/week"+' for Week '+str(wk))
		pl=ax.gridlines(crs=ccrs.PlateCarree(), draw_labels=True,
		 	linewidth=2, color='gray', alpha=0.5, linestyle='--')
		pl.xlabels_top = False
		pl.ylabels_left = True
		pl.ylabels_right = False
		pl.xformatter = LONGITUDE_FORMATTER
		pl.yformatter = LATITUDE_FORMATTER
		ax.add_feature(states_provinces, edgecolor='gray')
		ax.set_ybound(lower=lati, upper=late)
		CS=plt.pcolormesh(np.linspace(loni, loni+W*XD,num=W), np.linspace(lati+H*YD, lati, num=H), fprob,
    		vmin=0,vmax=100,
    		cmap=plt.cm.bwr,
    		transform=ccrs.PlateCarree())
		label = 'Probability (%) of Exceedance'

		plt.subplots_adjust(hspace=0)
		plt.subplots_adjust(bottom=0.15, top=0.9)
		cax = plt.axes([0.2, 0.08, 0.6, 0.04])
		cbar = plt.colorbar(CS,cax=cax, orientation='horizontal')
		cbar.set_label(label) #, rotation=270)
		f.close()

def pltprobff(thrs,ntrain,lon,lat,loni,lone,lati,late,fprefix,mpref,training_season,mon,fday,nwk):
	"""A simple function for ploting probabilities of exceedance and PDFs (for a given threshold)

	PARAMETERS
	----------
		thrs: the threshold, in the units of the predictand
		lon: longitude
		lat: latitude
	"""
	#Implement: read degrees of freedom from CPT file
	#Formally, for CCA, dof=ntrain - #CCAmodes -1 ; since ntrain is huge after concat, dof~=ntrain for now
	dof=ntrain

	#Read grads binary file size H, W  --it assumes all files have the same size, and that 2AFC exists
	with open('../output/'+fprefix+'_'+mpref+'_2AFC_'+training_season+'_wk1.ctl', "r") as fp:
		for line in lines_that_contain("XDEF", fp):
			W = int(line.split()[1])
			XD= float(line.split()[4])
	with open('../output/'+fprefix+'_'+mpref+'_2AFC_'+training_season+'_wk1.ctl', "r") as fp:
		for line in lines_that_contain("YDEF", fp):
			H = int(line.split()[1])
			YD= float(line.split()[4])
	with open('../output/'+fprefix+'_'+mpref+'FCST_Obs_'+training_season+'_'+str(mon)+str(fday)+'_wk1.ctl', "r") as fp:
		for line in lines_that_contain("TDEF", fp):
			T = int(line.split()[1])
			TD= 1  #not used

	#Find the gridbox:
	lonrange = np.linspace(loni, loni+W*XD,num=W)
	latrange = np.linspace(lati+H*YD, lati, num=H)  #need to reverse the latitudes because of CPT (GrADS YREV option)
	lon_grid, lat_grid = np.meshgrid(lonrange, latrange)
	a = abs(lat_grid-lat)+abs(lon_grid-lon)
	i,j = np.unravel_index(a.argmin(),a.shape)   #i:latitude   j:longitude

	#Now compute stuff and plot
	plt.figure(figsize=(15,15))

	for L in range(nwk):
		wk=L+1
		#Forecast files--------
		#Read mean
		#Since CPT writes grads files in sequential format, we need to excise the 4 bytes between records (recl)
		f=open('../output/'+fprefix+'_'+mpref+'FCST_mu_'+training_season+'_'+str(mon)+str(fday)+'_wk'+str(wk)+'.dat','rb')
		recl=struct.unpack('i',f.read(4))[0]
		numval=int(recl/np.dtype('float32').itemsize)
		#Now we read the field
		A=np.fromfile(f,dtype='float32',count=numval)
		muf = np.transpose(A.reshape((W, H), order='F'))
		muf[muf==-999.]=np.nan #identify NaNs
		muf=muf[i,j]

		#Read variance
		f=open('../output/'+fprefix+'_'+mpref+'FCST_var_'+training_season+'_'+str(mon)+str(fday)+'_wk'+str(wk)+'.dat','rb')
		recl=struct.unpack('i',f.read(4))[0]
		numval=int(recl/np.dtype('float32').itemsize)
		#Now we read the field
		A=np.fromfile(f,dtype='float32',count=numval)
		varf = np.transpose(A.reshape((W, H), order='F'))
		varf[varf==-999.]=np.nan #identify NaNs
		varf=varf[i,j]

		#Obs file--------
		#Compute obs mean and variance.
		#
		muc0=np.empty([T,H,W])  #define array for later use
		#Since CPT writes grads files in sequential format, we need to excise the 4 bytes between records (recl)
		f=open('../output/'+fprefix+'_'+mpref+'FCST_Obs_'+training_season+'_'+str(mon)+str(fday)+'_wk'+str(wk)+'.dat','rb')
		#cycle for all time steps  (same approach to read GrADS files as before, but now read T times)
		for it in range(T):
			#Now we read the field
			recl=struct.unpack('i',f.read(4))[0]
			numval=int(recl/np.dtype('float32').itemsize) #this if for each time stamp
			A0=np.fromfile(f,dtype='float32',count=numval)
			endrec=struct.unpack('i',f.read(4))[0]  #needed as Fortran sequential repeats the header at the end of the record!!!
			muc0[it,:,:]= np.transpose(A0.reshape((W, H), order='F'))

		muc0[muc0==-999.]=np.nan #identify NaNs
		#print(muc0)
		muc=np.nanmean(muc0, axis=0)  #axis 0 is T
		#print(muc)

		#Compute obs variance
		varc=np.nanvar(muc0, axis=0)  #axis 0 is T
		#Select gridbox values
		muc=muc[i,j]
		print(muc)
		varc=varc[i,j]

		#Compute scale parameter for the t-Student distribution
		scalef=np.sqrt(dof*varf)   #due to transformation from Gamma
		scalec=np.sqrt((dof-2)/dof*varc)

		x = np.linspace(min(t.ppf(0.00001, dof, loc=muf, scale=scalef),t.ppf(0.00001, dof, loc=muc, scale=scalec)),max(t.ppf(0.9999, dof, loc=muf, scale=scalef),t.ppf(0.9999, dof, loc=muc, scale=scalec)), 100)

		style = dict(size=10, color='black')

		#cprob = special.erfc((x-muc)/scalec)
		cprob = exceedprob(thrs,dof,muc,scalec)
		fprob = exceedprob(thrs,dof,muf,scalef)
		cprobth = round(t.sf(thrs, dof, loc=muc, scale=scalec)*100,2)
		fprobth = round(t.sf(thrs, dof, loc=muf, scale=scalef)*100,2)
		cpdf=t.pdf(x, dof, loc=muc, scale=scalec)*100
		fpdf=t.pdf(x, dof, loc=muf, scale=scalef)*100
		oddsrc =(fprobth/cprobth)

		fig, ax = plt.subplots(1, 2,figsize=(12,4))
		#font = {'family' : 'Palatino',
		#        'size'   : 16}
		#plt.rc('font', **font)
		#plt.rc('text', usetex=True)
		#plt.rc('font', family='serif')

		plt.subplot(1, 2, 1)
		plt.plot(x, t.sf(x, dof, loc=muc, scale=scalec)*100,'b-', lw=5, alpha=0.6, label='clim')
		plt.plot(x, t.sf(x, dof, loc=muf, scale=scalef)*100,'r-', lw=5, alpha=0.6, label='fcst')
		plt.axvline(x=thrs, color='k', linestyle='--')
		plt.plot(thrs, fprobth,'ok')
		plt.plot(thrs, cprobth,'ok')
		plt.text(thrs+0.05, cprobth, str(cprobth)+'%', **style)
		plt.text(thrs+0.05, fprobth, str(fprobth)+'%', **style)
		#plt.text(0.1, 10, r'$\frac{P(fcst)}{P(clim)}=$'+str(round(oddsrc,1)), **style)
		plt.text(min(t.ppf(0.0001, dof, loc=muf, scale=scalef),t.ppf(0.0001, dof, loc=muc, scale=scalec)), -20, 'P(fcst)/P(clim)='+str(round(oddsrc,1)), **style)
		plt.legend(loc='best', frameon=False)
		# Add title and axis names
		plt.title('Probabilities of Exceedance for Week '+str(wk))
		plt.xlabel('Rainfall')
		plt.ylabel('Probability (%)')
		# Limits for the Y axis
		plt.xlim(min(t.ppf(0.00001, dof, loc=muf, scale=scalef),t.ppf(0.00001, dof, loc=muc, scale=scalec)),max(t.ppf(0.9999, dof, loc=muf, scale=scalef),t.ppf(0.9999, dof, loc=muc, scale=scalec)))

		plt.subplot(1, 2, 2)
		plt.plot(x, cpdf,'b-', lw=5, alpha=0.6, label='clim')
		plt.plot(x, fpdf,'r-', lw=5, alpha=0.6, label='fcst')
		plt.axvline(x=thrs, color='k', linestyle='--')
		#fill area under the curve --not done
		#section = np.arange(min(t.ppf(0.00001, dof, loc=muf, scale=scalef),t.ppf(0.00001, dof, loc=muc, scale=scalec)), thrs, 1/20.)
		#plt.fill_between(section,f(section))
		plt.legend(loc='best', frameon=False)
		# Add title and axis names
		plt.title('Probability Density Functions for Week '+str(wk))
		plt.xlabel('Rainfall')
		plt.ylabel('')
		# Limits for the Y axis
		plt.xlim(min(t.ppf(0.00001, dof, loc=muf, scale=scalef),t.ppf(0.00001, dof, loc=muc, scale=scalec)),max(t.ppf(0.9999, dof, loc=muf, scale=scalef),t.ppf(0.9999, dof, loc=muc, scale=scalec)))

	plt.subplots_adjust(hspace=0)
	plt.subplots_adjust(bottom=0.15, top=0.9)
	#cax = plt.axes([0.2, 0.08, 0.6, 0.04])
	#cbar = plt.colorbar(CS,cax=cax, orientation='horizontal')
	#cbar.set_label(label) #, rotation=270)
	f.close()

def GetHindcasts(wlo1, elo1, sla1, nla1, day1, day2, fyr, mon, os, key, week, nlag, nday, training_season, hstep, model, hdate_last, force_download):
	if not force_download:
		try:
			ff=open("model_precip_"+mon+"_wk"+str(week)+".tsv", 'r')
			s = ff.readline()
		except OSError as err:
			print("OS error: {0}".format(err))
			print("Hindcasts file doesn't exist --downloading")
			force_download = True
	if force_download:
		#dictionary:
		dic = { 'CFSv2': 'https://iridl.ldeo.columbia.edu/SOURCES/.ECMWF/.S2S/.NCEP/.reforecast/.perturbed/.sfc_precip/.tp/Y/'+str(sla1)+'/'+str(nla1)+'/RANGE/X/'+str(wlo1)+'/'+str(elo1)+'/RANGE/S/-'+str(nlag-1)+'/1/0/shiftdatashort/%5BS_lag/M%5Daverage/3./mul/SOURCES/.ECMWF/.S2S/.NCEP/.reforecast/.control/.sfc_precip/.tp/S/-'+str(nlag-1)+'/1/0/shiftdatashort/%5BS_lag%5Daverage/add/4./div/X/'+str(wlo1)+'/'+str(elo1)+'/RANGE/Y/'+str(sla1)+'/'+str(nla1)+'/RANGE/L1/'+str(day1)+'/'+str(day2)+'/VALUES/%5BL1%5Ddifferences/S/('+training_season+')/VALUES/S/'+str(hstep)+'/STEP/dup/S/npts//I/exch/NewIntegerGRID/replaceGRID/dup/I/5/splitstreamgrid/%5BI2%5Daverage/sub/I/3/-1/roll/.S/replaceGRID/L1/S/add/0/RECHUNK//name//T/def/2/%7Bexch%5BL1/S%5D//I/nchunk/NewIntegerGRID/replaceGRIDstream%7Drepeat/use_as_grid/c://name//water_density/def/998/%28kg/m3%29/:c/div//mm/unitconvert//name/(tp)/def/grid://name/%28T%29/def//units/%28months%20since%201960-01-01%29/def//standard_name/%28time%29/def//pointwidth/1/def/16/Jan/1901/ensotime/12./16/Jan/3001/ensotime/:grid/use_as_grid//name/(tp)/def//units/(mm)/def//long_name/(precipitation_amount)/def/-999/setmissing_value/%5BX/Y%5D%5BT%5Dcptv10.tsv.gz',
				'ECMWF': 'https://iridl.ldeo.columbia.edu/SOURCES/.ECMWF/.S2S/.ECMF/.reforecast/.perturbed/.sfc_precip/.tp/Y/'+str(sla1)+'/'+str(nla1)+'/RANGE/X/'+str(wlo1)+'/'+str(elo1)+'/RANGE/L/('+str(day1)+')/('+str(day2)+')/VALUES/S/(0000%201%20'+mon+'%20'+str(fyr)+')%20(2300%2028%20'+mon+'%20'+str(fyr)+')/RANGE/%5BL%5Ddifferences/c%3A//name//water_density/def/998/(kg/m3)/%3Ac/div//mm/unitconvert/-999/setmissing_value/hdate/('+str(fyr-20)+')/('+str(hdate_last)+')/RANGE/dup/%5Bhdate%5Daverage/sub/%5BM%5Daverage/hdate//pointwidth/0/def/-6/shiftGRID/hdate/(days%20since%201960-01-01)/streamgridunitconvert/S/(days%20since%20'+str(fyr)+'-01-01)/streamgridunitconvert/S//units//days/def/L/hdate/add/add/0/RECHUNK/L/removeGRID//name//T/def/2/%7Bexch%5BS/hdate%5D//I/nchunk/NewIntegerGRID/replaceGRIDstream%7Drepeat/use_as_grid/T/grid%3A//name/(T)/def//units/(months%20since%201960-01-01)/def//standard_name/(time)/def//pointwidth/1/def/16/Jan/1901/ensotime/12./16/Jan/2060/ensotime/%3Agrid/replaceGRID//name/(tp)/def//units/(mm)/def//long_name/(precipitation_amount)/def/-999/setmissing_value/%5BX/Y%5D%5BT%5Dcptv10.tsv.gz',
				'GEFS':
'https://iridl.ldeo.columbia.edu/SOURCES/.Models/.SubX/.EMC/.GEFS/.hindcast/.pr/S/(0000%206%20Jan%201999)/(0000%2028%20Dec%202015)/RANGEEDGES/S/(days%20since%201999-01-01)/streamgridunitconvert/Y/'+str(sla1)+'/'+str(nla1)+'/RANGE/X/'+str(wlo1)+'/'+str(elo1)+'/RANGE/L/('+str(day1)+')/('+str(day2)+')/RANGEEDGES/%5BM%5Daverage/L/'+str(nday)+'/runningAverage/SOURCES/.Models/.SubX/.EMC/.GEFS/.hindcast/.dc9915/.pr/Y/'+str(sla1)+'/'+str(nla1)+'/RANGE/X/'+str(wlo1)+'/'+str(elo1)+'/RANGE/L/('+str(day1)+')/('+str(day2)+')/RANGEEDGES/L/'+str(nday)+'/runningAverage/S/(T)/renameGRID/pentadmean/T/(S)/renameGRID/%5BS%5DregridLinear/sub/S/('+training_season+')/VALUES/L/removeGRID/S/(T)/renameGRID/c%3A/0.001/(m3%20kg-1)/%3Ac/mul/c%3A/1000/(mm%20m-1)/%3Ac/mul/c%3A/86400/(s%20day-1)/%3Ac/mul/c%3A/7.0//units//days/def/%3Ac/mul/grid%3A//name/(T)/def//units/(months%20since%201960-01-01)/def//standard_name/(time)/def//pointwidth/1/def/16/Jan/1901/ensotime/12./16/Jan/2301/ensotime/%3Agrid/use_as_grid/-999/setmissing_value/%5BX/Y%5D%5BT%5Dcptv10.tsv.gz',
		}
		# calls curl to download data
		url=dic[model]
		print("\n Hindcasts URL: \n\n "+url)
		get_ipython().system("curl -g -k -b '__dlauth_id="+key+"' '"+url+"' > model_precip_"+mon+"_wk"+str(week)+".tsv.gz")
		get_ipython().system("gunzip -f model_precip_"+mon+"_wk"+str(week)+".tsv.gz")
		#! curl -g -k -b '__dlauth_id='$key'' ''$url'' > model_precip_${mo}.tsv

def GetHindcasts_RFREQ(wlo1, elo1, sla1, nla1, day1, day2, nday, fyr, mon, os, key, week, wetday_threshold, nlag, training_season, hstep,model, force_download):
	if not force_download:
		try:
			ff=open("model_RFREQ_"+mon+"_wk"+str(week)+".tsv", 'r')
			s = ff.readline()
		except OSError as err:
			print("OS error: {0}".format(err))
			print("Hindcasts file doesn't exist --downloading")
			force_download = True
	if force_download:
		#dictionary:
		dic = { 'CFSv2': 'https://iridl.ldeo.columbia.edu/SOURCES/.ECMWF/.S2S/.NCEP/.reforecast/.perturbed/.sfc_precip/.tp/Y/'+str(sla1)+'/'+str(nla1)+'/RANGE/X/'+str(wlo1)+'/'+str(elo1)+'/RANGE/S/-'+str(nlag-1)+'/1/0/shiftdatashort/%5BS_lag/M%5Daverage/3./mul/SOURCES/.ECMWF/.S2S/.NCEP/.reforecast/.control/.sfc_precip/.tp/S/-'+str(nlag-1)+'/1/0/shiftdatashort/%5BS_lag%5Daverage/add/4./div/X/'+str(wlo1)+'/'+str(elo1)+'/RANGE/Y/'+str(sla1)+'/'+str(nla1)+'/RANGE/L1/'+str(day1)+'/'+str(day2)+'/VALUES/%5BL1%5Ddifferences/S/('+training_season+')/VALUES/S/'+str(hstep)+'/STEP/dup/S/npts//I/exch/NewIntegerGRID/replaceGRID/dup/I/5/splitstreamgrid/%5BI2%5Daverage/sub/I/3/-1/roll/.S/replaceGRID/L1/S/add/0/RECHUNK//name//T/def/2/%7Bexch%5BL1/S%5D//I/nchunk/NewIntegerGRID/replaceGRIDstream%7Drepeat/use_as_grid/c://name//water_density/def/998/%28kg/m3%29/:c/div//mm/unitconvert//name/(tp)/def/grid://name/%28T%29/def//units/%28months%20since%201960-01-01%29/def//standard_name/%28time%29/def//pointwidth/1/def/16/Jan/1901/ensotime/12./16/Jan/3001/ensotime/:grid/use_as_grid//name/(fp)/def//units/(unitless)/def//long_name/(rainfall_freq)/def/-999/setmissing_value/%5BX/Y%5D%5BT%5Dcptv10.tsv.gz',
				'ECMWF': 'https://iridl.ldeo.columbia.edu/SOURCES/.ECMWF/.S2S/.ECMF/.reforecast/.perturbed/.sfc_precip/.tp/Y/'+str(sla1)+'/'+str(nla1)+'/RANGE/X/'+str(wlo1)+'/'+str(elo1)+'/RANGE/L/('+str(day1)+')/('+str(day2)+')/VALUES/(0000%201%20'+mon+'%20'+str(fyr)+')%20(2300%2028%20'+mon+'%20'+str(fyr)+')/RANGE/%5BL%5Ddifferences/c%3A//name//water_density/def/998/(kg/m3)/%3Ac/div//mm/unitconvert/'+str(wetday_threshold)+'/flagge/T/'+str(nday)+'/runningAverage/'+str(nday)+'.0/mul/-999/setmissing_value/hdate/('+str(fyr-20)+')/('+str(fyr-1)+')/RANGE/dup/%5Bhdate%5Daverage/sub/%5BM%5Daverage/hdate//pointwidth/0/def/-6/shiftGRID/hdate/(days%20since%201960-01-01)/streamgridunitconvert/S/(days%20since%20'+str(fyr)+'-01-01)/streamgridunitconvert/S//units//days/def/L/hdate/add/add/0/RECHUNK/L/removeGRID//name//T/def/2/%7Bexch%5BS/hdate%5D//I/nchunk/NewIntegerGRID/replaceGRIDstream%7Drepeat/use_as_grid/T/grid%3A//name/(T)/def//units/(months%20since%201960-01-01)/def//standard_name/(time)/def//pointwidth/1/def/16/Jan/1901/ensotime/12./16/Jan/2060/ensotime/%3Agrid/replaceGRID//name/(fp)/def//units/(unitless)/def//long_name/(rainfall_freq)/def/-999/setmissing_value/%5BX/Y%5D%5BT%5Dcptv10.tsv.gz'
		}
		# calls curl to download data
		url=dic[model]
		print("\n Hindcasts URL: \n\n "+url)
		get_ipython().system("curl -g -k -b '__dlauth_id="+key+"' '"+url+"' > model_RFREQ_"+mon+"_wk"+str(week)+".tsv.gz")
		get_ipython().system("gunzip -f model_RFREQ_"+mon+"_wk"+str(week)+".tsv.gz")
		#! curl -g -k -b '__dlauth_id='$key'' ''$url'' > model_precip_${mo}.tsv

def GetObs(day1, day2, mon, fyr, wlo2, elo2, sla2, nla2, nday, key, week, nlag, training_season, hstep, model, obs_source, hdate_last, force_download):
	if not force_download:
		try:
			ff=open("obs_precip_"+mon+"_wk"+str(week)+".tsv", 'r')
			s = ff.readline()
		except OSError as err:
			print("OS error: {0}".format(err))
			print("Obs precip file doesn't exist --downloading")
			force_download = True
	if force_download:
		#dictionary:
		dic = {'CFSv2':                'https://iridl.ldeo.columbia.edu/SOURCES/.ECMWF/.S2S/.NCEP/.reforecast/.control/.sfc_precip/.tp/Y/'+str(sla2)+'/'+str(nla2)+'/RANGE/X/'+str(wlo2)+'/'+str(elo2)+'/RANGE/S/-'+str(nlag-1)+'/1/0/shiftdatashort/%5BS_lag%5Daverage/S/(0000%201%20Jan%201999)/(0000%2031%20Dec%202010)/RANGEEDGES/L1/'+str(day1)+'/'+str(day2)+'/VALUES/%5BL1%5Ddifferences/S/('+training_season+')/VALUES/S/'+str(hstep)+'/STEP/L1/S/add/0/RECHUNK/name//T/def/2/%7Bexch%5BL1/S%5D//I/nchunk/NewIntegerGRID/replaceGRIDstream%7Drepeat/use_as_grid/'+obs_source+'/Y/'+str(sla2)+'/'+str(nla2)+'/RANGE/X/'+str(wlo2)+'/'+str(elo2)+'/RANGE/T/(days%20since%201960-01-01)/streamgridunitconvert/3/flagge/dup/pentadmean/%5BT%5D/regridLinear/sub/T/'+str(nday)+'/runningAverage/c%3A/7.0//units//days/def/%3Ac/mul/T/2/index/.T/SAMPLE/nip/dup/T/npts//I/exch/NewIntegerGRID/replaceGRID/I/3/-1/roll/.T/replaceGRID/grid%3A//name/(T)/def//units/(months%20since%201960-01-01)/def//standard_name/(time)/def//pointwidth/1/def/16/Jan/1901/ensotime/12./16/Jan/3001/ensotime/%3Agrid/use_as_grid/-999/setmissing_value/%5BX/Y%5D%5BT%5Dcptv10.tsv.gz',
			   'ECMWF': 'https://iridl.ldeo.columbia.edu/SOURCES/.ECMWF/.S2S/.ECMF/.reforecast/.perturbed/.sfc_precip/.tp/Y/'+str(sla2)+'/'+str(nla2)+'/RANGE/X/'+str(wlo2)+'/'+str(elo2)+'/RANGE/L/('+str(day1)+')/('+str(day2)+')/VALUES/S/(0000%201%20'+mon+'%20'+str(fyr)+')%20(2300%2028%20'+mon+'%20'+str(fyr)+')/RANGE/%5BL%5Ddifferences/c%3A//name//water_density/def/998/(kg/m3)/%3Ac/div//mm/unitconvert/-999/setmissing_value/hdate/('+str(fyr-20)+')/('+str(hdate_last)+')/RANGE/dup/%5Bhdate%5Daverage/sub/%5BM%5Daverage/hdate//pointwidth/0/def/-6/shiftGRID/hdate/(days%20since%201960-01-01)/streamgridunitconvert/S/(days%20since%20'+str(fyr)+'-01-01)/streamgridunitconvert/S//units//days/def/L/hdate/add/add/0/RECHUNK/L/removeGRID//name//T/def/2/%7Bexch%5BS/hdate%5D//I/nchunk/NewIntegerGRID/replaceGRIDstream%7Drepeat/use_as_grid/'+obs_source+'/Y/'+str(sla2)+'/'+str(nla2)+'/RANGE/X/'+str(wlo2)+'/'+str(elo2)+'/RANGE/T/(days%20since%201960-01-01)/streamgridunitconvert/T/'+str(nday)+'/runningAverage/'+str(nday)+'.0/mul/T/2/index/.T/SAMPLE/dup%5BT%5Daverage/sub/-999/setmissing_value/nip/T/grid%3A//name/(T)/def//units/(months%20since%201960-01-01)/def//standard_name/(time)/def//pointwidth/1/def/16/Jan/1901/ensotime/12./16/Jan/2060/ensotime/%3Agrid/replaceGRID//name/(tp)/def//units/(mm)/def//long_name/(precipitation_amount)/def/-999/setmissing_value/%5BX/Y%5D%5BT%5Dcptv10.tsv.gz',
			   'GEFS':       'https://iridl.ldeo.columbia.edu/SOURCES/.Models/.SubX/.EMC/.GEFS/.hindcast/.pr/S/(0000%206%20Jan%201999)/(0000%2028%20Dec%202015)/RANGEEDGES/L/('+str(day1)+')/('+str(day2)+')/RANGEEDGES/L/'+str(nday)+'/runningAverage/S/('+training_season+')/VALUES/L/S/add/0/RECHUNK//name//T/def/2/%7Bexch%5BL/S%5D//I/nchunk/NewIntegerGRID/replaceGRIDstream%7Drepeat/use_as_grid/'+obs_source+'/Y/'+str(sla2)+'/'+str(nla2)+'/RANGE/X/'+str(wlo2)+'/'+str(elo2)+'/RANGE/T/(days%20since%201960-01-01)/streamgridunitconvert/dup/pentadmean/%5BT%5D/regridLinear/sub/T/'+str(nday)+'/runningAverage/c%3A/7.0//units//days/def/%3Ac/mul/T/2/index/.T/SAMPLE/nip/dup/T/npts//I/exch/NewIntegerGRID/replaceGRID/I/3/-1/roll/.T/replaceGRID/grid%3A//name/(T)/def//units/(months%20since%201960-01-01)/def//standard_name/(time)/def//pointwidth/1/def/16/Jan/1901/ensotime/12./16/Jan/2301/ensotime/%3Agrid/use_as_grid/-999/setmissing_value/%5BX/Y%5D%5BT%5Dcptv10.tsv.gz'
			  }
		# calls curl to download data
		url=dic[model]
		print("\n Obs (Rainfall) data URL: \n\n "+url)
		get_ipython().system("curl -g -k -b '__dlauth_id="+key+"' '"+url+"' > obs_precip_"+mon+"_wk"+str(week)+".tsv.gz")
		get_ipython().system("gunzip -f obs_precip_"+mon+"_wk"+str(week)+".tsv.gz")
		#curl -g -k -b '__dlauth_id='$key'' ''$url'' > obs_precip_${mo}.tsv

def GetObs_RFREQ(day1, day2, mon, fyr, wlo2, elo2, sla2, nla2, nday, key, week, wetday_threshold, threshold_pctle, nlag, training_season, hstep, model, obs_source, force_download):
	if not force_download:
		try:
			ff=open("obs_RFREQ_"+mon+"_wk"+str(week)+".tsv", 'r')
			s = ff.readline()
		except OSError as err:
			print("OS error: {0}".format(err))
			print("Obs freq-rainfall file doesn't exist --downloading")
			force_download = True
	if force_download:
		#dictionaries:
		if threshold_pctle:
				dic = { 'CFSv2': 'https://iridl.ldeo.columbia.edu/SOURCES/.ECMWF/.S2S/.NCEP/.reforecast/.control/.sfc_precip/.tp/Y/'+str(sla2)+'/'+str(nla2)+'/RANGE/X/'+str(wlo2)+'/'+str(elo2)+'/RANGE/S/-'+str(nlag-1)+'/1/0/shiftdatashort/%5BS_lag%5Daverage/S/(0000%201%20Jan%201999)/(0000%2031%20Dec%202010)/RANGEEDGES/L1/'+str(day1)+'/'+str(day2)+'/VALUES/%5BL1%5Ddifferences/S/('+training_season+')/VALUES/S/'+str(hstep)+'/STEP/L1/S/add/0/RECHUNK//name//T/def/2/%7Bexch%5BL1/S%5D//I/nchunk/NewIntegerGRID/replaceGRIDstream%7Drepeat/use_as_grid/SOURCES/.NASA/.GES-DAAC/.TRMM_L3/.TRMM_3B42/.v7/.daily/.precipitation/X/0./1.5/360./GRID/Y/-50/1.5/50/GRID/Y/'+str(sla2)+'/'+str(nla2)+'/RANGE/X/'+str(wlo2)+'/'+str(elo2)+'/RANGE/T/(days%20since%201960-01-01)/streamgridunitconvert/T/(1%20Jan%201999)/(31%20Dec%202011)/RANGEEDGES/%5BT%5Dpercentileover/'+str(wetday_threshold)+'/flagle/T/'+str(nday)+'/runningAverage/'+str(nday)+'/mul/T/2/index/.T/SAMPLE/nip/dup/T/npts//I/exch/NewIntegerGRID/replaceGRID/dup/I/5/splitstreamgrid/%5BI2%5Daverage/sub/I/3/-1/roll/.T/replaceGRID/-999/setmissing_value/grid%3A//name/(T)/def//units/(months%20since%201960-01-01)/def//standard_name/(time)/def//pointwidth/1/def/16/Jan/1901/ensotime/12./16/Jan/3001/ensotime/%3Agrid/use_as_grid//name/(fp)/def//units/(unitless)/def//long_name/(rainfall_freq)/def/-999/setmissing_value/%5BX/Y%5D%5BT%5Dcptv10.tsv.gz',
						'ECMWF':'https://iridl.ldeo.columbia.edu/SOURCES/.ECMWF/.S2S/.ECMF/.reforecast/.perturbed/.sfc_precip/.tp/Y/'+str(sla2)+'/'+str(nla2)+'/RANGE/X/'+str(wlo2)+'/'+str(elo2)+'/RANGE/L/('+str(day1)+')/('+str(day2)+')/VALUES/S/(0000%201%20'+mon+'%20'+str(fyr)+')%20(2300%2028%20'+mon+'%20'+str(fyr)+')/RANGE/%5BL%5Ddifferences/c%3A//name//water_density/def/998/(kg/m3)/%3Ac/div//mm/unitconvert/-999/setmissing_value/hdate/('+str(fyr-20)+')/('+str(fyr-1)+')/RANGE/dup/%5Bhdate%5Daverage/sub/%5BM%5Daverage/hdate//pointwidth/0/def/-6/shiftGRID/hdate/(days%20since%201960-01-01)/streamgridunitconvert/S/(days%20since%20'+str(fyr)+'-01-01)/streamgridunitconvert/S//units//days/def/L/hdate/add/add/0/RECHUNK/L/removeGRID//name//T/def/2/%7Bexch%5BS/hdate%5D//I/nchunk/NewIntegerGRID/replaceGRIDstream%7Drepeat/use_as_grid/SOURCES/.NASA/.GES-DAAC/.TRMM_L3/.TRMM_3B42/.v7/.daily/.precipitation/X/0./1.5/360./GRID/Y/-50/1.5/50/GRID/Y/'+str(sla2)+'/'+str(nla2)+'/RANGE/X/'+str(wlo2)+'/'+str(elo2)+'/RANGE/T/(days%20since%201960-01-01)/streamgridunitconvert/%5BT%5Dpercentileover/'+str(wetday_threshold)+'/flagle/T/'+str(nday)+'/runningAverage/'+str(nday)+'.0/mul/T/2/index/.T/SAMPLE/nip/dup/T/npts//I/exch/NewIntegerGRID/replaceGRID/dup/I/5/splitstreamgrid/%5BI2%5Daverage/sub/I/3/-1/roll/.T/replaceGRID/-999/setmissing_value/grid%3A//name/(T)/def//units/(months%20since%201960-01-01)/def//standard_name/(time)/def//pointwidth/1/def/16/Jan/1901/ensotime/12./16/Jan/2060/ensotime/%3Agrid/use_as_grid//name/(fp)/def//units/(unitless)/def//long_name/(rainfall_freq)/def/-999/setmissing_value/%5BX/Y%5D%5BT%5Dcptv10.tsv.gz'
						}
		else:
				dic = { 'CFSv2':                     'https://iridl.ldeo.columbia.edu/SOURCES/.ECMWF/.S2S/.NCEP/.reforecast/.control/.sfc_precip/.tp/Y/'+str(sla2)+'/'+str(nla2)+'/RANGE/X/'+str(wlo2)+'/'+str(elo2)+'/RANGE/S/-'+str(nlag-1)+'/1/0/shiftdatashort/%5BS_lag%5Daverage/S/(0000%201%20Jan%201999)/(0000%2031%20Dec%202010)/RANGEEDGES/L1/'+str(day1)+'/'+str(day2)+'/VALUES/%5BL1%5Ddifferences/S/('+training_season+')/VALUES/S/'+str(hstep)+'/STEP/L1/S/add/0/RECHUNK/name//T/def/2/%7Bexch%5BL1/S%5D//I/nchunk/NewIntegerGRID/replaceGRIDstream%7Drepeat/use_as_grid/SOURCES/.NASA/.GES-DAAC/.TRMM_L3/.TRMM_3B42/.v7/.daily/.precipitation/X/0./1.5/360./GRID/Y/-50/1.5/50/GRID/Y/'+str(sla2)+'/'+str(nla2)+'/RANGE/X/'+str(wlo2)+'/'+str(elo2)+'/RANGE/T/(days%20since%201960-01-01)/streamgridunitconvert/'+str(wetday_threshold)+'/flagge/dup/pentadmean/%5BT%5D/regridLinear/sub/T/'+str(nday)+'/runningAverage/c%3A/7.0//units//days/def/%3Ac/mul/T/2/index/.T/SAMPLE/nip/dup/T/npts//I/exch/NewIntegerGRID/replaceGRID/I/3/-1/roll/.T/replaceGRID/grid%3A//name/(T)/def//units/(months%20since%201960-01-01)/def//standard_name/(time)/def//pointwidth/1/def/16/Jan/1901/ensotime/12./16/Jan/3001/ensotime/%3Agrid/use_as_grid/-999/setmissing_value/%5BX/Y%5D%5BT%5Dcptv10.tsv.gz',
						'ECMWF': 'https://iridl.ldeo.columbia.edu/SOURCES/.ECMWF/.S2S/.ECMF/.reforecast/.perturbed/.sfc_precip/.tp/Y/'+str(sla2)+'/'+str(nla2)+'/RANGE/X/'+str(wlo2)+'/'+str(elo2)+'/RANGE/L/('+str(day1)+')/('+str(day2)+')/VALUES/S/(0000%201%20'+mon+'%20'+str(fyr)+')%20(2300%2028%20'+mon+'%20'+str(fyr)+')/RANGE/%5BL%5Ddifferences/c%3A//name//water_density/def/998/(kg/m3)/%3Ac/div//mm/unitconvert/-999/setmissing_value/hdate/('+str(fyr-20)+')/('+str(fyr-1)+')/RANGE/dup/%5Bhdate%5Daverage/sub/%5BM%5Daverage/hdate//pointwidth/0/def/-6/shiftGRID/hdate/(days%20since%201960-01-01)/streamgridunitconvert/S/(days%20since%20'+str(fyr)+'-01-01)/streamgridunitconvert/S//units//days/def/L/hdate/add/add/0/RECHUNK/L/removeGRID//name//T/def/2/%7Bexch%5BS/hdate%5D//I/nchunk/NewIntegerGRID/replaceGRIDstream%7Drepeat/use_as_grid/SOURCES/.NASA/.GES-DAAC/.TRMM_L3/.TRMM_3B42/.v7/.daily/.precipitation/X/0./1.5/360./GRID/Y/-50/1.5/50/GRID/Y/'+str(sla2)+'/'+str(nla2)+'/RANGE/X/'+str(wlo2)+'/'+str(elo2)+'/RANGE/T/(days%20since%201960-01-01)/streamgridunitconvert/'+str(wetday_threshold)+'/flagge/T/'+str(nday)+'/runningAverage/'+str(nday)+'.0/mul/T/2/index/.T/SAMPLE/nip/dup/T/npts//I/exch/NewIntegerGRID/replaceGRID/dup/I/5/splitstreamgrid/%5BI2%5Daverage/sub/I/3/-1/roll/.T/replaceGRID/-999/setmissing_value/grid%3A//name/(T)/def//units/(months%20since%201960-01-01)/def//standard_name/(time)/def//pointwidth/1/def/16/Jan/1901/ensotime/12./16/Jan/2060/ensotime/%3Agrid/use_as_grid//name/(fp)/def//units/(unitless)/def//long_name/(rainfall_freq)/def/-999/setmissing_value/%5BX/Y%5D%5BT%5Dcptv10.tsv.gz',
						'GEFS':       'https://iridl.ldeo.columbia.edu/SOURCES/.Models/.SubX/.EMC/.GEFS/.hindcast/.pr/S/(0000%206%20Jan%201999)/(0000%2028%20Dec%202015)/RANGEEDGES/L/('+str(day1)+')/('+str(day2)+')/RANGEEDGES/L/'+str(nday)+'/runningAverage/S/('+training_season+')/VALUES/L/S/add/0/RECHUNK//name//T/def/2/%7Bexch%5BL/S%5D//I/nchunk/NewIntegerGRID/replaceGRIDstream%7Drepeat/use_as_grid/SOURCES/.NASA/.GES-DAAC/.TRMM_L3/.TRMM_3B42/.v7/.daily/.precipitation/X/0./1.5/360./GRID/Y/-50/1.5/50/GRID/Y/'+str(sla2)+'/'+str(nla2)+'/RANGE/X/'+str(wlo2)+'/'+str(elo2)+'/RANGE/T/(days%20since%201960-01-01)/streamgridunitconvert/'+str(wetday_threshold)+'/flagge/dup/pentadmean/%5BT%5D/regridLinear/sub/T/'+str(nday)+'/runningAverage/c%3A/7.0//units//days/def/%3Ac/mul/T/2/index/.T/SAMPLE/nip/dup/T/npts//I/exch/NewIntegerGRID/replaceGRID/I/3/-1/roll/.T/replaceGRID/grid%3A//name/(T)/def//units/(months%20since%201960-01-01)/def//standard_name/(time)/def//pointwidth/1/def/16/Jan/1901/ensotime/12./16/Jan/2301/ensotime/%3Agrid/use_as_grid/-999/setmissing_value/%5BX/Y%5D%5BT%5Dcptv10.tsv.gz'
						}
		# calls curl to download data
		url=dic[model]
		print("\n Obs (Freq) data URL: \n\n "+url)
		get_ipython().system("curl -g -k -b '__dlauth_id="+key+"' '"+url+"' > obs_RFREQ_"+mon+"_wk"+str(week)+".tsv.gz")
		get_ipython().system("gunzip -f obs_RFREQ_"+mon+"_wk"+str(week)+".tsv.gz")
		#curl -g -k -b '__dlauth_id='$key'' ''$url'' > obs_precip_${mo}.tsv

def GetForecast(day1, day2, fday, mon, fyr, nday, wlo1, elo1, sla1, nla1, key, week, nlag, model, force_download):
	if not force_download:
		try:
			ff=open("modelfcst_precip_"+mon+"_fday"+str(fday)+"_wk"+str(week)+".tsv", 'r')
			s = ff.readline()
		except OSError as err:
			print("OS error: {0}".format(err))
			print("Forecasts file doesn't exist --downloading")
			force_download = True
	if force_download:
		#dictionary:
		dic = {	'CFSv2': 'https://iridl.ldeo.columbia.edu/SOURCES/.ECMWF/.S2S/.NCEP/.reforecast/.perturbed/.sfc_precip/.tp/Y/'+str(sla1)+'/'+str(nla1)+'/RANGE/X/'+str(wlo1)+'/'+str(elo1)+'/RANGE/S/-'+str(nlag-1)+'/1/0/shiftdatashort/%5BS_lag/M%5Daverage/3./mul/SOURCES/.ECMWF/.S2S/.NCEP/.reforecast/.control/.sfc_precip/.tp/Y/'+str(sla1)+'/'+str(nla1)+'/RANGE/X/'+str(wlo1)+'/'+str(elo1)+'/RANGE/S/-'+str(nlag-1)+'/1/0/shiftdatashort/%5BS_lag%5Daverage/add/4./div/X/'+str(wlo1)+'/'+str(elo1)+'/RANGE/Y/'+str(sla1)+'/'+str(nla1)+'/RANGE/L1/'+str(day1)+'/'+str(day2)+'/VALUES/%5BL1%5Ddifferences/L1/removeGRID/S/(0000%20'+str(fday)+'%20'+mon+')/VALUES/%5BS%5Daverage/c%3A//name//water_density/def/998/(kg/m3)/%3Ac/div//mm/unitconvert/SOURCES/.NOAA/.NCEP/.EMC/.CFSv2/.6_hourly_rotating/.FLXF/.surface/.PRATE/%5BL%5D1/0.0/boxAverage/S/-'+str(nlag-1)+'/1/0/shiftdatashort/%5BS_lag/M%5Daverage/S/(0000%20'+str(fday)+'%20'+mon+'%20'+str(fyr)+')VALUE/%5BX/Y%5DregridLinear/L/'+str(day1)+'/'+str(day2)+'/RANGEEDGES/%5BL%5Daverage/%5BS%5Daverage/c%3A//name//water_density/def/998/(kg/m3)/%3Ac/div/(mm/day)/unitconvert/'+str(nday)+'/mul//units/(mm)/def/exch/sub/X/'+str(wlo1)+'/'+str(elo1)+'/RANGE/Y/'+str(sla1)+'/'+str(nla1)+'/RANGE/grid%3A//name/(T)/def//units/(months%20since%201960-01-01)/def//standard_name/(time)/def//pointwidth/1/def/1/Jan/3001/ensotime/12.0/1/Jan/3001/ensotime/%3Agrid/addGRID/T//pointwidth/0/def/pop//name/(tp)/def//units/(mm)/def//long_name/(precipitation_amount)/def/-999/setmissing_value/%5BX/Y%5D%5BT%5Dcptv10.tsv.gz',
				'ECMWF': 'https://iridl.ldeo.columbia.edu/SOURCES/.ECMWF/.S2S/.ECMF/.forecast/.perturbed/.sfc_precip/.tp/Y/'+str(sla1)+'/'+str(nla1)+'/RANGE/X/'+str(wlo1)+'/'+str(elo1)+'/RANGE/L/('+str(day1)+')/('+str(day2)+')/VALUES/S/(0000%20'+str(fday)+'%20'+mon+'%20'+str(fyr)+')/VALUE/%5BL%5Ddifferences/%5BM%5Daverage/SOURCES/.ECMWF/.S2S/.ECMF/.reforecast/.perturbed/.sfc_precip/.tp/Y/'+str(sla1)+'/'+str(nla1)+'/RANGE/X/'+str(wlo1)+'/'+str(elo1)+'/RANGE/L/('+str(day1)+')/('+str(day2)+')/VALUES/S/(0000%20'+str(fday)+'%20'+mon+'%20'+str(fyr)+')/VALUE/%5BL%5Ddifferences/%5BM%5Daverage/%5Bhdate%5Daverage/sub/c%3A//name//water_density/def/998/(kg/m3)/%3Ac/div//mm/unitconvert/grid%3A//name/(T)/def//units/(months%20since%201960-01-01)/def//standard_name/(time)/def//pointwidth/1/def/1/Jan/3001/ensotime/12.0/1/Jan/3001/ensotime/%3Agrid/addGRID/T//pointwidth/0/def/pop//name/(tp)/def//units/(mm)/def//long_name/(precipitation_amount)/def/-999/setmissing_value/%5BX/Y%5D%5BT%5Dcptv10.tsv.gz',
				'GEFS':           'https://iridl.ldeo.columbia.edu/SOURCES/.Models/.SubX/.EMC/.GEFS/.forecast/.pr/S/(0000%20'+str(fday)+'%20'+mon+'%20'+str(fyr)+')/VALUES/Y/'+str(sla1)+'/'+str(nla1)+'/RANGE/X/'+str(wlo1)+'/'+str(elo1)+'/RANGE/L/('+str(day1)+')/('+str(day2)+')/RANGEEDGES/%5BM%5Daverage/L/'+str(nday)+'/runningAverage/SOURCES/.Models/.SubX/.EMC/.GEFS/.hindcast/.dc9915/.pr/Y/'+str(sla1)+'/'+str(nla1)+'/RANGE/X/'+str(wlo1)+'/'+str(elo1)+'/RANGE/L/('+str(day1)+')/('+str(day2)+')/RANGEEDGES/L/'+str(nday)+'/runningAverage/S/(T)/renameGRID/pentadmean/T/(S)/renameGRID/%5BS%5DregridLinear/S/1/setgridtype/pop/S/2/index/.S/SAMPLE/sub/c%3A/0.001/(m3%20kg-1)/%3Ac/mul/c%3A/1000/(mm%20m-1)/%3Ac/mul/c%3A/86400/(s%20day-1)/%3Ac/mul/c%3A/7.0//units//days/def/%3Ac/mul/S/(T)/renameGRID/grid%3A//name/(T)/def//units/(months%20since%201960-01-01)/def//standard_name/(time)/def//pointwidth/1/def/16/Jan/3001/ensotime/12.0/16/Jan/3001/ensotime/%3Agrid/use_as_grid/-999/setmissing_value/%5BX/Y%5D%5BT%5Dcptv10.tsv.gz'
			  }
		# calls curl to download data
		url=dic[model]
		print("\n Forecast URL: \n\n "+url)
		get_ipython().system("curl -g -k -b '__dlauth_id="+key+"' '"+url+"' > modelfcst_precip_"+mon+"_fday"+str(fday)+"_wk"+str(week)+".tsv.gz")
		get_ipython().system("gunzip -f modelfcst_precip_"+mon+"_fday"+str(fday)+"_wk"+str(week)+".tsv.gz")
		#curl -g -k -b '__dlauth_id='$key'' ''$url'' > modelfcst_precip_fday${fday}.tsv

def GetForecast_RFREQ(day1, day2, fday, mon, fyr, nday, wlo1, elo1, sla1, nla1, key, week, wetday_threshold, nlag, model, force_download):
	if not force_download:
		try:
			ff=open("modelfcst_RFREQ_"+mon+"_fday"+str(fday)+"_wk"+str(week)+".tsv", 'r')
			s = ff.readline()
		except OSError as err:
			print("OS error: {0}".format(err))
			print("Forecasts file doesn't exist --downloading")
			force_download = True
	if force_download:
		#dictionary:  #CFSv2 needs to be transformed to RFREQ!
		dic = {	'CFSv2': 'https://iridl.ldeo.columbia.edu/SOURCES/.ECMWF/.S2S/.NCEP/.reforecast/.perturbed/.sfc_precip/.tp/Y/'+str(sla1)+'/'+str(nla1)+'/RANGE/X/'+str(wlo1)+'/'+str(elo1)+'/RANGE/S/-'+str(nlag-1)+'/1/0/shiftdatashort/%5BS_lag/M%5Daverage/3./mul/SOURCES/.ECMWF/.S2S/.NCEP/.reforecast/.control/.sfc_precip/.tp/Y/'+str(sla1)+'/'+str(nla1)+'/RANGE/X/'+str(wlo1)+'/'+str(elo1)+'/RANGE/S/-'+str(nlag-1)+'/1/0/shiftdatashort/%5BS_lag%5Daverage/add/4./div/X/'+str(wlo1)+'/'+str(elo1)+'/RANGE/Y/'+str(sla1)+'/'+str(nla1)+'/RANGE/L1/'+str(day1)+'/'+str(day2)+'/VALUES/%5BL1%5Ddifferences/L1/removeGRID/S/(0000%20'+str(fday)+'%20'+mon+')/VALUES/%5BS%5Daverage/c%3A//name//water_density/def/998/(kg/m3)/%3Ac/div//mm/unitconvert/SOURCES/.NOAA/.NCEP/.EMC/.CFSv2/.6_hourly_rotating/.FLXF/.surface/.PRATE/%5BL%5D1/0.0/boxAverage/S/-'+str(nlag-1)+'/1/0/shiftdatashort/%5BS_lag/M%5Daverage/S/(0000%20'+str(fday)+'%20'+mon+'%20'+str(fyr)+')VALUE/%5BX/Y%5DregridLinear/L/'+str(day1)+'/'+str(day2)+'/RANGEEDGES/%5BL%5Daverage/%5BS%5Daverage/c%3A//name//water_density/def/998/(kg/m3)/%3Ac/div/(mm/day)/unitconvert/'+str(nday)+'/mul//units/(mm)/def/exch/sub/X/'+str(wlo1)+'/'+str(elo1)+'/RANGE/Y/'+str(sla1)+'/'+str(nla1)+'/RANGE/grid%3A//name/(T)/def//units/(months%20since%201960-01-01)/def//standard_name/(time)/def//pointwidth/1/def/1/Jan/3001/ensotime/12.0/1/Jan/3001/ensotime/%3Agrid/addGRID/T//pointwidth/0/def/pop//name/(fp)/def//units/(unitless)/def//long_name/(rainfall_freq)/def/-999/setmissing_value/%5BX/Y%5D%5BT%5Dcptv10.tsv.gz',
				'ECMWF': 'https://iridl.ldeo.columbia.edu/SOURCES/.ECMWF/.S2S/.ECMF/.forecast/.perturbed/.sfc_precip/.tp/Y/'+str(sla1)+'/'+str(nla1)+'/RANGE/X/'+str(wlo1)+'/'+str(elo1)+'/RANGE/L/('+str(day1)+')/('+str(day2)+')/VALUES/S/(0000%20'+str(fday)+'%20'+mon+'%20'+str(fyr)+')/VALUE/%5BL%5Ddifferences/c%3A//name//water_density/def/998/(kg/m3)/%3Ac/div//mm/unitconvert/'+str(wetday_threshold)+'/flagge/T/'+str(nday)+'/runningAverage/'+str(nday)+'.0/mul/SOURCES/.ECMWF/.S2S/.ECMF/.reforecast/.perturbed/.sfc_precip/.tp/Y/'+str(sla1)+'/'+str(nla1)+'/RANGE/X/'+str(wlo1)+'/'+str(elo1)+'/RANGE/L/('+str(day1-1)+')/('+str(day2)+')/VALUES/S/(0000%20'+str(fday)+'%20'+mon+'%20'+str(fyr)+')/VALUE/%5BL%5Ddifferences/c%3A//name//water_density/def/998/(kg/m3)/%3Ac/div//mm/unitconvert/'+str(wetday_threshold)+'/flagge/T/'+str(nday)+'/runningAverage/'+str(nday)+'.0/mul/%5Bhdate%5Daverage/sub/grid%3A//name/(T)/def//units/(months%20since%201960-01-01)/def//standard_name/(time)/def//pointwidth/1/def/1/Jan/3001/ensotime/12.0/1/Jan/3001/ensotime/%3Agrid/addGRID/T//pointwidth/0/def/pop//name/(fp)/def//units/(unitless)/def//long_name/(rainfall_freq)/def/-999/setmissing_value/%5BX/Y%5D%5BT%5Dcptv10.tsv.gz'
			  }
		# calls curl to download data
		url=dic[model]
		print("\n Forecast URL: \n\n "+url)
		get_ipython().system("curl -g -k -b '__dlauth_id="+key+"' '"+url+"' > modelfcst_RFREQ_"+mon+"_fday"+str(fday)+"_wk"+str(week)+".tsv.gz")
		get_ipython().system("gunzip -f modelfcst_RFREQ_"+mon+"_fday"+str(fday)+"_wk"+str(week)+".tsv.gz")
		#curl -g -k -b '__dlauth_id='$key'' ''$url'' > modelfcst_precip_fday${fday}.tsv

def CPTscript(mon,fday,wk,nla1,sla1,wlo1,elo1,nla2,sla2,wlo2,elo2,fprefix,mpref,training_season,ntrain,rainfall_frequency,MOS):
		"""Function to write CPT namelist file

		"""
		# Set up CPT parameter file
		f=open("params","w")
		if MOS=='CCA':
			# Opens CCA
			f.write("611\n")
		elif MOS=='PCR':
			# Opens PCR
			f.write("612\n")
		elif MOS=='PCR':
			# Opens GCM; because the calibration takes place via sklearn.linear_model (in the Jupyter notebook)
			f.write("614\n")
		elif MOS=='None':
			# Opens GCM (no calibration performed in CPT)
			f.write("614\n")
		else:
			print ("MOS option is invalid")

		# First, ask CPT to stop if error is encountered
		f.write("571\n")
		f.write("3\n")

		# Opens X input file
		f.write("1\n")
		if rainfall_frequency:
			file='../input/model_precip_'+mon+'_wk'+str(wk)+'.tsv\n'
		else:
			file='../input/model_precip_'+mon+'_wk'+str(wk)+'.tsv\n'
		f.write(file)
		# Nothernmost latitude
		f.write(str(nla1)+'\n')
		# Southernmost latitude
		f.write(str(sla1)+'\n')
		# Westernmost longitude
		f.write(str(wlo1)+'\n')
		# Easternmost longitude
		f.write(str(elo1)+'\n')
		if MOS=='CCA' or MOS=='PCR':
			# Minimum number of X modes
			f.write("1\n")
			# Maximum number of X modes
			f.write("10\n")

			# Opens forecast (X) file
			f.write("3\n")
			if rainfall_frequency:
				file='../input/modelfcst_precip_'+mon+'_fday'+str(fday)+'_wk'+str(wk)+'.tsv\n'
			else:
				file='../input/modelfcst_precip_'+mon+'_fday'+str(fday)+'_wk'+str(wk)+'.tsv\n'
			f.write(file)

		# Opens Y input file
		f.write("2\n")
		if rainfall_frequency:
			file='../input/obs_RFREQ_'+mon+'_wk'+str(wk)+'.tsv\n'
		else:
			file='../input/obs_precip_'+mon+'_wk'+str(wk)+'.tsv\n'
		f.write(file)
		# Nothernmost latitude
		f.write(str(nla2)+'\n')
		# Southernmost latitude
		f.write(str(sla2)+'\n')
		# Westernmost longitude
		f.write(str(wlo2)+'\n')
		# Easternmost longitude
		f.write(str(elo2)+'\n')
		if MOS=='CCA':
			# Minimum number of Y modes
			f.write("1\n")
			# Maximum number of Y modes
			f.write("10\n")

			# Minimum number of CCA modes
			f.write("1\n")
			# Maximum number of CCAmodes
			f.write("5\n")

		# X training period
		f.write("4\n")
		# First year of X training period
		f.write("1901\n")
		# Y training period
		f.write("5\n")
		# First year of Y training period
		f.write("1901\n")

		# Goodness index
		f.write("531\n")
		# Kendall's tau
		f.write("3\n")

		# Option: Length of training period
		f.write("7\n")
		# Length of training period
		f.write(str(ntrain)+'\n')
		#	%store 55 >> params
		# Option: Length of cross-validation window
		f.write("8\n")
		# Enter length
		f.write("3\n")

		# Turn ON Transform predictand data
		f.write("541\n")
		# Turn ON zero bound for Y data	 (automatically on by CPT if variable is precip)
		#f.write("542\n")
		# Turn ON synchronous predictors
		f.write("545\n")
		# Turn ON p-values for masking maps
		#f.write("561\n")

		### Missing value options
		f.write("544\n")
		# Missing value X flag:
		blurb='-999\n'
		f.write(blurb)
		# Maximum % of missing values
		f.write("10\n")
		# Maximum % of missing gridpoints
		f.write("10\n")
		# Number of near-neighbors
		f.write("1\n")
		# Missing value replacement : best-near-neighbors
		f.write("4\n")
		# Y missing value flag
		blurb='-999\n'
		f.write(blurb)
		# Maximum % of missing values
		f.write("10\n")
		# Maximum % of missing stations
		f.write("10\n")
		# Number of near-neighbors
		f.write("1\n")
		# Best near neighbor
		f.write("4\n")

		# Transformation settings
		#f.write("554\n")
		# Empirical distribution
		#f.write("1\n")

		#######BUILD MODEL AND VALIDATE IT	!!!!!

		# NB: Default output format is GrADS format
		# select output format
		f.write("131\n")
		# GrADS format
		f.write("3\n")

		# save goodness index
		f.write("112\n")
		file='../output/'+fprefix+'_'+mpref+'_Kendallstau_'+training_season+'_wk'+str(wk)+'\n'
		f.write(file)

		# Cross-validation
		f.write("311\n")

		# cross-validated skill maps
		f.write("413\n")
		# save Pearson's Correlation
		f.write("1\n")
		file='../output/'+fprefix+'_'+mpref+'_Pearson_'+training_season+'_wk'+str(wk)+'\n'
		f.write(file)

		# cross-validated skill maps
		f.write("413\n")
		# save Spearmans Correlation
		f.write("2\n")
		file='../output/'+fprefix+'_'+mpref+'_Spearman_'+training_season+'_wk'+str(wk)+'\n'
		f.write(file)

		# cross-validated skill maps
		f.write("413\n")
		# save 2AFC score
		f.write("3\n")
		file='../output/'+fprefix+'_'+mpref+'_2AFC_'+training_season+'_wk'+str(wk)+'\n'
		f.write(file)

		# cross-validated skill maps
		f.write("413\n")
		# save RocBelow score
		f.write("10\n")
		file='../output/'+fprefix+'_'+mpref+'_RocBelow_'+training_season+'_wk'+str(wk)+'\n'
		f.write(file)

		# cross-validated skill maps
		f.write("413\n")
		# save RocAbove score
		f.write("11\n")
		file='../output/'+fprefix+'_'+mpref+'_RocAbove_'+training_season+'_wk'+str(wk)+'\n'
		f.write(file)

		if MOS=='CCA' or MOS=='PCR':   #DO NOT USE CPT to compute probabilities if MOS='None' --use IRIDL for direct counting
			#######FORECAST(S)	!!!!!
			# Probabilistic (3 categories) maps
			f.write("455\n")
			# Output results
			f.write("111\n")
			# Forecast probabilities
			f.write("501\n")
			file='../output/'+fprefix+'_'+mpref+'FCST_P_'+training_season+'_'+mon+str(fday)+'_wk'+str(wk)+'\n'
			f.write(file)
			#502 # Forecast odds
			#Exit submenu
			f.write("0\n")

			# Compute deterministc values and prediction limits
			f.write("454\n")
			# Output results
			f.write("111\n")
			# Forecast values
			f.write("511\n")
			file='../output/'+fprefix+'_'+mpref+'FCST_V_'+training_season+'_'+mon+str(fday)+'_wk'+str(wk)+'\n'
			f.write(file)
			#502 # Forecast odds


			#######Following files are used to plot the flexible format
			# Save cross-validated predictions
			f.write("201\n")
			file='../output/'+fprefix+'_'+mpref+'FCST_xvPr_'+training_season+'_'+mon+str(fday)+'_wk'+str(wk)+'\n'
			f.write(file)
			# Save deterministic forecasts [mu for Gaussian fcst pdf]
			f.write("511\n")
			file='../output/'+fprefix+'_'+mpref+'FCST_mu_'+training_season+'_'+mon+str(fday)+'_wk'+str(wk)+'\n'
			f.write(file)
			# Save prediction error variance [sigma^2 for Gaussian fcst pdf]
			f.write("514\n")
			file='../output/'+fprefix+'_'+mpref+'FCST_var_'+training_season+'_'+mon+str(fday)+'_wk'+str(wk)+'\n'
			f.write(file)
			# Save z
			f.write("532\n")
			file='../output/'+fprefix+'_'+mpref+'FCST_z_'+training_season+'_'+mon+str(fday)+'_wk'+str(wk)+'\n'
			f.write(file)
			# Save predictand [to build predictand pdf]
			f.write("102\n")
			file='../output/'+fprefix+'_'+mpref+'FCST_Obs_'+training_season+'_'+mon+str(fday)+'_wk'+str(wk)+'\n'
			f.write(file)

			#Exit submenu
			f.write("0\n")

			# Stop saving  (not needed in newest version of CPT)

		# Exit
		f.write("0\n")

		f.close()
