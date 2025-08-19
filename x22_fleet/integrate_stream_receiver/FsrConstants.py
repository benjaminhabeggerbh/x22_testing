class FullScaleRangeConstants:
    accFactor_x22 = 0.488/1000              # for 16g see Doc/lsm6dsrx-2.pdf, page 10,      data stored as g (1=9.81m/s^)
    gyroFactor_x22 = 140/1000               # for 4000dps see Doc/lsm6dsrx-2.pdf, page 10,  data stored as degree / s           
    magFactor_x22 = 1 / 1711                # see Doc/lis3mdl-2.pdf, page 3,                data stored as Gauss
