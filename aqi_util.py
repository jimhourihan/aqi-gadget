
US_EPA_aqi_ranges_pm25 = [
    # C, Clow, Chigh, iLow, iHigh, label, RGB
    (12, (0.0, 12.0, 0.0, 50.0, "Good", (0, 1.0, 0))),
    (35.4, (12.1, 35.4, 51.0, 100.0, "Moderate", (1.0, 1.0, 0))),
    (55.4, (35.5, 55.4, 101.0, 150.0, "Unhealthy (SG)", (1.0, 0.5, 0))),
    (150.4, (55.5, 150.4, 151.0, 200.0, "Unhealthy", (1.0, 0, 0))),
    (250.4, (150.5, 250.4, 201.0, 300.0, "Very Unhealthy", (0.57, 0.0, 0.3))),
    (350.4, (250.5, 350.4, 301.0, 400.0, "Hazardous", (0.5, 0, 0.15))),
    (500.0, (350.4, 500.0, 401.0, 500.0, "Hazardous", (0.5, 0, 0.15))),
    (500000.0, (500.0, 50000.0, 501.0, 500000.0, "Off Scale", (0.5, 0, 0.15)))
]

IN_CPCB_aqi_ranges_pm25 = [
    (30, (0.0, 30.0, 0, 50,  "Good", (0, .8, 0))),
    (60, (30.1, 60, 50, 100, "Satisfactory", (.4, .8, 0))),
    (90, (60.1, 90, 100, 200, "Moderately Polluted", (1, 1, 0))),
    (120, (90.1, 120, 200, 300, "Poor", (1, .6, 0))),
    (250, (120.1, 250, 300, 400, "Very Poor", (1, 0, 0))),
    (370, (250.1, 370, 400, 500, "Severe", (.51, .36, .23))), # made up upper bounds
    (50000, (370.1, 50000, 500, 60056, "Off Scale", (.51 / 2.0, .36 / 2.0, .23 / 2.0))), # extrapolate
]   

pm25_aqi_types = {
    'US' : US_EPA_aqi_ranges_pm25,
    'IN' : IN_CPCB_aqi_ranges_pm25,
}   

aqi_type_description = {
    'US' : 'US EPA',
    'IN' : 'Indian CPCB',
}

def LRAPA_25_correction (c):
    cc = c / 2.0 - 0.66
    return cc if cc > 0.0 else 0.0

def AQandU_25_correction (c):
    cc = c * 0.851 - 1.1644
    return cc if cc > 0.0 else 0.0

def EPA_25_correction (c, rh):
    cc = (0.534 * c - 0.0844 * rh + 5.604) if c < 250 else c
    return cc if cc > 0.0 else 0.0

def EPA_100_correction (c, rh):
    return c

aqi_corrections = {
    'EPA' : EPA_25_correction,
    'AQandU' : lambda c,h: AQandU_25_correction(c),
    'LRAPA' : lambda c,h: LRAPA_25_correction(c),
    'Native' : lambda c,h: c,
}

def aqi_correction_func (name):
    if name not in aqi_corrections:
        name = 'Native'
    return aqi_corrections[name]

def rgb_from_aqi (aqi):
    for i in rgb_list:
        if aqi < i[0]:
            return i[-1]
    return None

def aqi_from_concentration (c, pmsize, index_code = 'US'):
    (il, ih, cl, ch, t) = (0, 0, 0, 0, "")
    if index_code not in pm25_aqi_types:
        index_code = 'US'
    range_list = pm25_aqi_types[index_code]
    rgb = (1,1,1)

    for i in range_list:
        if c <= i[0]:
            (cl, ch, il, ih, t, rgb) = i[1]
            break

    aqi = (ih - il) / (ch - cl) * (c - cl) + il
    return (int(aqi), t, rgb)
