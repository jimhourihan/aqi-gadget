
def LRAPA_25_correction (c):
    cc = c / 2.0 - 0.66
    return cc if cc > 0.0 else 0.0

def AQandU_25_correction (c):
    cc = c * 0.851 - 1.1644
    return cc if cc > 0.0 else 0.0

def EPA_25_correction (c, rh):
    cc = 0.534 * c - 0.0844 * rh + 5.604
    return cc if cc > 0.0 else 0.0

def EPA_10_correction (c, rh):
    return c

def rgb_shade_from_aqi (aqi):
    if aqi < 50:
        u = aqi / 50.0
        return (u, 1.0, 0.0)
    elif aqi < 100:
        u = (aqi - 50.0) / 50.0
        return (1.0, 1.0 - u * 0.5, 0.0)
    elif aqi < 150:
        u = (aqi - 100) / 50.0
        return (1.0, 0.5 - u * 0.5, 0.0)
    elif aqi < 200:
        u = (aqi - 150) / 50.0
        return (1.0 - u * 0.5, 0.5 - u * 0.5, 0.0)
    elif aqi < 300:
        u = (aqi - 200) / 100.0
        return (1.0 - u * 0.43, 0.5 - u * 0.5, 0.3 * u)
    else:
        return (0.5, 0, 0.14)

rgb_list = [
    (50, (0, 1.0, 0)),
    (100, (1.0, 1.0, 0)),
    (150, (1.0, 0.5, 0)),
    (200, (1.0, 0, 0)),
    (300, (0.57, 0.0, 0.3)),
    (10000, (0.5, 0, 0.15))
]

US_EPA_aqi_ranges = [
    (12, 54, (0.0, 12.0, 0.0, 50.0, "Good")),
    (35.4, 154, (12.1, 35.4, 51.0, 100.0, "Moderate")),
    (55.4, 254, (35.5, 55.4, 101.0, 150.0, "Unhealthy (SG)")),
    (150.4, 354, (55.5, 150.4, 151.0, 200.0, "Unhealthy")),
    (250.4, 424, (150.5, 250.4, 201.0, 300.0, "Very Unhealthy")),
    (350.4, 504, (250.5, 350.4, 301.0, 400.0, "Hazardous")),
    (500.0, 604, (350.4, 500.0, 401.0, 500.0, "Hazardous")),
    (500000.0, 500000.0, (500.0, 50000.0, 501.0, 500000.0, "Off Scale"))
]

#IN_CPCB_aqi_ranges = [
#    (30, 50, (

def rgb_from_aqi (aqi):
    for i in rgb_list:
        if aqi < i[0]:
            return i[-1]
    return None

def aqi_from_concentration (c, pmsize, country_code = "US"):
    (il, ih, cl, ch, t) = (0, 0, 0, 0, "")
    #range_list = US_EPA_aqi_ranges if country_code == "US" else IN_CPCB_aqi_ranges
    range_list = US_EPA_aqi_ranges
    index = 0 if pmsize == 2.5 else 1

    for i in range_list:
        if c <= i[index]:
            (cl, ch, il, ih, t) = i[2]
            break

    aqi = (ih - il) / (ch - cl) * (c - cl) + il
    rgb = rgb_from_aqi(aqi)
    return (int(aqi), t, rgb)
