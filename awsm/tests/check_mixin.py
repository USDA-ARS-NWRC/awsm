
class CheckPysnobalOutputs(object):
    """Check the AWSM test case for all the variables. To be used as a
    mixin for tests to avoid these tests running more than once.

    Example:
        TestSomethingNew(CheckPysnobalOutputs, AWSMTestCase)
    """

    def test_thickness(self):
        self.compare_netcdf_files('ipysnobal.nc', 'thickness')

    def test_snow_density(self):
        self.compare_netcdf_files('ipysnobal.nc', 'snow_density')

    def test_specific_mass(self):
        self.compare_netcdf_files('ipysnobal.nc', 'specific_mass')

    def test_liquid_water(self):
        self.compare_netcdf_files('ipysnobal.nc', 'liquid_water')

    def test_temperature_surface(self):
        self.compare_netcdf_files('ipysnobal.nc', 'temperature_surface')

    def test_temperature_lower(self):
        self.compare_netcdf_files('ipysnobal.nc', 'temperature_lower')

    def test_temperature_snowcover(self):
        self.compare_netcdf_files('ipysnobal.nc', 'temperature_snowcover')

    def test_thickness_lower(self):
        self.compare_netcdf_files('ipysnobal.nc', 'thickness_lower')

    def test_water_saturation(self):
        self.compare_netcdf_files('ipysnobal.nc', 'water_saturation')

    def test_net_radiation(self):
        self.compare_netcdf_files('ipysnobal.nc', 'net_radiation')

    def test_sensible_heat(self):
        self.compare_netcdf_files('ipysnobal.nc', 'sensible_heat')

    def test_latent_heat(self):
        self.compare_netcdf_files('ipysnobal.nc', 'latent_heat')

    def test_snow_soil(self):
        self.compare_netcdf_files('ipysnobal.nc', 'snow_soil')

    def test_precip_advected(self):
        self.compare_netcdf_files('ipysnobal.nc', 'precip_advected')

    def test_sum_energy_balance(self):
        self.compare_netcdf_files('ipysnobal.nc', 'sum_energy_balance')

    def test_evaporation(self):
        self.compare_netcdf_files('ipysnobal.nc', 'evaporation')

    def test_snowmelt(self):
        self.compare_netcdf_files('ipysnobal.nc', 'snowmelt')

    def test_surface_water_input(self):
        self.compare_netcdf_files('ipysnobal.nc', 'surface_water_input')

    def test_cold_content(self):
        self.compare_netcdf_files('ipysnobal.nc', 'cold_content')


class CheckModelChange(object):

    def test_model_change_depth(self):
        self.compare_netcdf_files('model_lidar_change.nc', 'depth_change')

    def test_model_change_density(self):
        self.compare_netcdf_files('model_lidar_change.nc', 'rho_change')

    def test_model_change_swe(self):
        self.compare_netcdf_files('model_lidar_change.nc', 'swe_change')
