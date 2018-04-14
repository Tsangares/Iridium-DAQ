from agilent import Agilent4156
from power_supply import PowerSupplyFactory
import sys
import argparse
import configparser


class Daq(object):
    """

    """
    list_data = []
    compliance = [0]*4
    def __init__(self, smu_config, smu_global_params, keithley_global_params, output_file):
        (scan_smu, scan_config, time_delay) = smu_global_params
        self.output_file = output_file

        self.scope = Agilent4156()
        self.scope.configure_measurement(1)
        self.scope.configure_sampling_measurement(hold_time=smu_global_params[2])

        self.supply = PowerSupplyFactory.factory(keithley_global_params[0])
        self.supply.configure_measurement(1, 0, keithley_global_params[2])

        if __debug__:
            print("DEBUG: SMU_CONFIG:{}".format(smu_config))
            print("DEBUG: SMU_GLOBAL:{}".format(smu_global_params))
            print("DEBUG: KEITHLEY:{}".format(keithley_global_params))

        for ch_num in range(0, 4):
            (ch_on, ch_comp, ch_alias) = smu_config[ch_num]
            self.compliance[ch_num] = ch_comp
            if not ch_on:
                continue
            self.scope.configure_channel(ch_num, False, 0)
            #if ch_num is not int(scan_smu.split("_")[1])-1:
            self.scope.configure_constant_output(ch_num, 0, ch_comp)
        self.sample_smu = int(scan_smu.split("_")[1])-1
        print("SCAN_SMU:{}".format(self.sample_smu))

        self.scope.configure_integration_time(_int_time=1)
        self.iv_loop(smu_global_params[1], keithley_global_params[1])
        self.dump_data()
        self.scope.close()
        self.supply.supply.close()

    def dump_data(self):
        with open(self.output_file+".csv", "w") as f:
            f.write("KEITHLEY_V,KEITHLEY_I,SMU_1_V,SMU_1_I,SMU_2_V,SMU_2_I\n")
            for event in self.list_data:
                (k_iv, smu_1_iv, smu_2_iv) = event
                f.write("{},{},{},{},{},{}\n".format(
                    k_iv[0], k_iv[1],
                    smu_1_iv[0], smu_1_iv[1],
                    smu_2_iv[0], smu_2_iv[1]
                ))

    def iv_loop(self, analyzer_voltages, keithley_voltages):

        for keithley_region in keithley_voltages:

            voltage_list = keithley_region.strip().split(" ")

            start_volt = float(voltage_list[0])
            end_volt = float(voltage_list[1])
            step_volt = float(voltage_list[2])

            if start_volt > end_volt:
                step_volt = -1*abs(step_volt)

            num_steps = int((end_volt-start_volt)/step_volt)+1

            for volt in range(num_steps):

                self.supply.set_output(volt*step_volt+start_volt)
                if __debug__:
                    print("KVOLT:{}".format(volt*step_volt+start_volt))
                k_current = self.supply.get_current()

                for analyzer_region in analyzer_voltages:

                    anal_voltage_list = analyzer_region.strip().split(" ")
                    anal_start_volt = float(anal_voltage_list[0])
                    anal_end_volt = float(anal_voltage_list[1])
                    anal_step_volt = float(anal_voltage_list[2])

                    if anal_start_volt > anal_end_volt:
                        anal_step_volt = -1 * abs(anal_step_volt)

                    anal_num_steps = int((anal_end_volt - anal_start_volt) / anal_step_volt)+1

                    for anal_volt in range(anal_num_steps):
                        currents = []
                        if __debug__:
                            print("AVOLT:{}".format(anal_volt * anal_step_volt + anal_start_volt))
                        self.scope.configure_constant_output(
                            str(int(self.sample_smu)+1),
                            anal_volt * anal_step_volt + anal_start_volt,
                            self.compliance[self.sample_smu]
                        )
                        self.scope.measurement_actions()
                        self.scope.wait_for_acquisition()
                        currents.append(self.scope.read_trace_data("I1"))
                        currents.append(self.scope.read_trace_data("I2"))
                        if self.sample_smu == 0:
                            self.list_data.append((
                                (volt*step_volt+start_volt, k_current),
                                (anal_volt * anal_step_volt + anal_start_volt, currents[0]),
                                (0, currents[1])
                            ))
                        else:
                            self.list_data.append((
                                (volt*step_volt+start_volt, k_current),
                                (0, currents[0]),
                                (anal_volt * anal_step_volt + anal_start_volt, currents[1])
                            ))

        """
        scope = Agilent4156()
        scope.configure_measurement(1)
        scope.configure_channel(0, standby=False, _mode=0)
        scope.configure_channel(1, standby=False, _mode=4)
        scope.configure_channel(2, standby=False, _mode=4)
        scope.configure_channel(3, standby=False, _mode=4)
        scope.configure_sampling_measurement()
        scope.configure_constant_output(1, 1.0, 1e-1)
        scope.measurement_actions()
        scope.wait_for_acquisition()
        print(scope.read_trace_data())
        scope.close()
        """


if __name__ == "__main__":

    # Info section
    print("""Welcome to
    
 ______            __        __  __                         
/      |          /  |      /  |/  |                        
$$$$$$/   ______  $$/   ____$$ |$$/  __    __  _____  ____  
  $$ |   /      \ /  | /    $$ |/  |/  |  /  |/     \/    \ 
  $$ |  /$$$$$$  |$$ |/$$$$$$$ |$$ |$$ |  $$ |$$$$$$ $$$$  |
  $$ |  $$ |  $$/ $$ |$$ |  $$ |$$ |$$ |  $$ |$$ | $$ | $$ |
 _$$ |_ $$ |      $$ |$$ \__$$ |$$ |$$ \__$$ |$$ | $$ | $$ |
/ $$   |$$ |      $$ |$$    $$ |$$ |$$    $$/ $$ | $$ | $$ |
$$$$$$/ $$/       $$/  $$$$$$$/ $$/  $$$$$$/  $$/  $$/  $$/ 
    """)
    print("For support or bug report submission: Please email Ric <therickyross2@gmail.com>")
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", help="Config file with settings for DAQ")
    parser.add_argument("--outfile", help="Output filename")
    args = parser.parse_args()
    if args.config:
        print("Loading in {}".format(args.config))
    else:
        print("No config file specified. Exiting now")
        sys.exit(1)
    if args.outfile:
        print("Saving to {}".format(args.outfile))
    else:
        print("No output file specified. Using latest.csv")
        args.outfile = "latest_daq"
    config = configparser.RawConfigParser(allow_no_value=True)
    config.read_file(open(args.config))
    smu_config = []
    for num_smu in range(1, 5):
        ch_on = config.getboolean("Parameter Analyzer", "smu{}".format(num_smu))
        ch_comp = config.getfloat("Parameter Analyzer", "smu{}_compliance".format(num_smu))
        ch_alias = config.get("Parameter Analyzer", "smu{}_alias".format(num_smu))
        smu_config.append((ch_on, ch_comp, ch_alias))
    scan_smu = config.get("Parameter Analyzer", "scan_smu")
    scan_config = config.get("Parameter Analyzer", "scan_config").split(",")
    time_delay = config.getfloat("Parameter Analyzer", "delay")
    smu_global_params = [scan_smu, scan_config, time_delay]
    keithley_choice = config.get("HV Supply", "keithley")
    keithley_step = config.get("HV Supply", "step_config").split(",")
    keithley_compliance = config.getfloat("HV Supply", "compliance")
    keithley_global_params = [keithley_choice, keithley_step, keithley_compliance]

    iridium_daq = Daq(smu_config, smu_global_params, keithley_global_params, args.outfile)




