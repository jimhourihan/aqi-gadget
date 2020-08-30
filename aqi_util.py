
def LRAPA_correction (c):
    return c / 2.0 - 0.66

def AQandU_correction (c):
    return c * 0.851 - 1.1644

def aqi_from_concentration (c):
    il = 0.0
    ih = 0.0
    cl = 0.0
    ch = 0.0
    t = ""

    if c <= 12:
        (cl, ch, il, ih, t) = (0.0, 12.0, 0.0, 50.0, "Good")
    elif c <= 35.4:
        (cl, ch, il, ih, t) = (12.1, 35.4, 51.0, 100.0, "Moderate")
    elif c <= 55.4:
        (cl, ch, il, ih, t) = (35.5, 55.4, 101.0, 150.0, "Unhealthy for Selective Groups")
    elif c <= 150.4:
        (cl, ch, il, ih, t) = (55.5, 150.4, 151.0, 200.0, "Unhealthy")
    elif c <= 250.4:
        (cl, ch, il, ih, t) = (150.5, 250.4, 201.0, 300.0, "Very Unhealthy")
    elif c <= 350.4:
        (cl, ch, il, ih, t) = (250.5, 350.4, 301.0, 400.0, "Hazardous")
    elif c <= 500.0:
        (cl, ch, il, ih, t) = (350.4, 500.0, 401.0, 500.0, "Hazardous2")

    aqi = (ih - il) / (ch - cl) * (c - cl) + il

    rgb = (1.0, 1.0, 1.0)
    
    if aqi < 50:
        rgb = (0, 1.0, 0)
    if aqi >= 50 and aqi < 100:
        rgb = (1.0, 1.0, 0)
    elif aqi >= 100 and aqi < 150:
        rgb = (1.0, 0.5, 0)
    elif aqi >= 150 and aqi < 200:
        rgb = (1.0, 0, 0)
    elif aqi >= 200:
        rgb = (0.5, 0, 0.18)

    return (int(aqi), t, rgb)
