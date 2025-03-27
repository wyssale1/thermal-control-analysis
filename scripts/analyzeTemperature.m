%% Enhanced Offset Analysis with Ambient Temperature Consideration
% This updated version of analyzeMeasurementsV2 includes ambient temperature
% effects in the temperature offset model

%% File Setup with Specific Path
% Set the exact file path and check if it exists
% Add all source directories to the MATLAB path
addpath(genpath('../src/'));

% Define path to data folder
dataDir = '../data/raw/';

% Define path to specific file
filepath = fullfile(dataDir, '10.01.25,09.51,50.0_5.0_1.0_15.xlsx');

% Create output directory if it doesn't exist
outputDir = '../data/processed/';
if ~exist(outputDir, 'dir')
    mkdir(outputDir);
end

% Extract filename from the path
[~, filename, ext] = fileparts(filepath);
filename = [filename, ext];
fprintf('Processing file: %s\n', filename);

% Initialize variables to store results
all_target_temps = [];
all_liquid_offsets = [];
all_ambient_temps = [];  % New: Store ambient temperatures
measurement_names = {};

% Initialize figure for plotting
figure('Name', 'Temperature Offsets vs Target Temperatures', 'Position', [100 100 1200 800]);

% Read measurement data and settings
try
    fprintf('Reading measurement data...\n');
    data = readMeasurement(filename, filepath);
    settings = readSettings(filename);
    fprintf('Successfully read data with dimensions: %d x %d\n', size(data, 1), size(data, 2));
catch ME
    error('Error reading file: %s\nError message: %s', filepath, ME.message);
end

% Split data into temperature steps
try
    fprintf('Splitting data into temperature steps...\n');
    steps = splitTempSteps(data, settings);
    fprintf('Successfully split data into %d temperature steps.\n', length(steps));
catch ME
    error('Error splitting temperature steps: %s', ME.message);
end

% Process each temperature step
for step_idx = 1:length(steps)
    step_data = steps{step_idx};
    
    % Extract step name for plotting
    if settings.increment > 0
        step_name = sprintf('%s: %.1f°C', settings.date, settings.startTemp + (step_idx-1)*settings.increment);
    else
        step_name = sprintf('%s: %.1f°C', settings.date, settings.startTemp + (step_idx-1)*settings.increment);
    end
    
    fprintf('\nProcessing step %d of %d: %s\n', step_idx, length(steps), step_name);
    
    % Extract offset information and ambient temperature
    [table, offset, t_stable, ambient_temp] = extractOffset(step_data, step_name);
    
    % Store results
    target_temp = step_data(1, 4);  % Target temperature is in column 4
    all_target_temps = [all_target_temps; target_temp];
    all_liquid_offsets = [all_liquid_offsets; offset];
    all_ambient_temps = [all_ambient_temps; ambient_temp];
    measurement_names{end+1} = step_name;
end

% Fit polynomial model without ambient temperature (original approach)
p_original = polyfit(all_target_temps, all_liquid_offsets, 2);
fprintf('Original model: y = %.6fx² + %.6fx + %.6f\n', p_original(1), p_original(2), p_original(3));

% Fit enhanced model with ambient temperature
% Create design matrix [target_temp^2, target_temp, (ambient_temp - reference_temp), 1]
reference_temp = 20;  % Reference ambient temperature in °C
X = [all_target_temps.^2, all_target_temps, all_ambient_temps - reference_temp, ones(size(all_target_temps))];
coeffs = X \ all_liquid_offsets;  % Least squares solution

fprintf('Enhanced model: y = %.6fx² + %.6fx + %.6f + %.6f*(T_ambient - %.1f)\n', ...
    coeffs(1), coeffs(2), coeffs(4), coeffs(3), reference_temp);

% Calculate R-squared for both models to compare fit quality
y_pred_original = polyval(p_original, all_target_temps);
SS_total = sum((all_liquid_offsets - mean(all_liquid_offsets)).^2);
SS_residual_original = sum((all_liquid_offsets - y_pred_original).^2);
R_squared_original = 1 - SS_residual_original/SS_total;

y_pred_enhanced = X * coeffs;
SS_residual_enhanced = sum((all_liquid_offsets - y_pred_enhanced).^2);
R_squared_enhanced = 1 - SS_residual_enhanced/SS_total;

fprintf('Original model R² = %.4f\n', R_squared_original);
fprintf('Enhanced model R² = %.4f\n', R_squared_enhanced);

% Plot the results
figure('Name', 'Offset Models Comparison', 'Position', [100 100 1400 800]);

% Plot 1: Offsets vs Target Temperature with both model fits
subplot(2,2,1)
scatter(all_target_temps, all_liquid_offsets, 50, all_ambient_temps, 'filled');
colormap jet
c = colorbar;
c.Label.String = 'Ambient Temperature (°C)';
hold on;

% Create smooth curves for models
temp_range = linspace(min(all_target_temps), max(all_target_temps), 100)';
mean_ambient = mean(all_ambient_temps);
X_smooth = [temp_range.^2, temp_range, ones(size(temp_range))*0, ones(size(temp_range))];

plot(temp_range, polyval(p_original, temp_range), 'r-', 'LineWidth', 2);
plot(temp_range, X_smooth * coeffs, 'g-', 'LineWidth', 2);
xlabel('Target Temperature (°C)');
ylabel('Liquid Temperature Offset (°C)');
title('Liquid Temperature Offset vs Target Temperature');
legend('Measured Data', 'Original Model', 'Enhanced Model (at reference ambient temp)');
grid on;

% Plot 2: Offset model residuals
subplot(2,2,2)
plot(all_target_temps, all_liquid_offsets - y_pred_original, 'ro', 'MarkerSize', 8);
hold on;
plot(all_target_temps, all_liquid_offsets - y_pred_enhanced, 'go', 'MarkerSize', 8);
plot([min(all_target_temps), max(all_target_temps)], [0, 0], 'k--');
xlabel('Target Temperature (°C)');
ylabel('Residuals (°C)');
title('Model Residuals');
legend('Original Model', 'Enhanced Model');
grid on;

% Plot 3: Ambient temperature effect visualization
subplot(2,2,3)
temp_levels = [mean(all_ambient_temps)-3, mean(all_ambient_temps), mean(all_ambient_temps)+3];
colors = ['b', 'g', 'r'];
legend_entries = {};

for i = 1:length(temp_levels)
    ambient = temp_levels(i);
    X_with_ambient = [temp_range.^2, temp_range, ones(size(temp_range))*(ambient-reference_temp), ones(size(temp_range))];
    plot(temp_range, X_with_ambient * coeffs, colors(i), 'LineWidth', 2);
    hold on;
    legend_entries{i} = sprintf('Ambient = %.1f°C', ambient);
end

xlabel('Target Temperature (°C)');
ylabel('Predicted Liquid Temperature Offset (°C)');
title('Effect of Ambient Temperature on Offset Model');
legend(legend_entries);
grid on;

% Plot 4: 3D visualization of the model
subplot(2,2,4)
[X_grid, Y_grid] = meshgrid(linspace(min(all_target_temps), max(all_target_temps), 50), ...
                           linspace(min(all_ambient_temps), max(all_ambient_temps), 50));
Z_grid = zeros(size(X_grid));

for i = 1:size(X_grid, 1)
    for j = 1:size(X_grid, 2)
        target_temp = X_grid(i,j);
        ambient_temp = Y_grid(i,j);
        X_point = [target_temp^2, target_temp, ambient_temp-reference_temp, 1];
        Z_grid(i,j) = X_point * coeffs;
    end
end

surf(X_grid, Y_grid, Z_grid);
colormap jet
hold on;
scatter3(all_target_temps, all_ambient_temps, all_liquid_offsets, 50, 'ko', 'filled');
xlabel('Target Temperature (°C)');
ylabel('Ambient Temperature (°C)');
zlabel('Liquid Temperature Offset (°C)');
title('3D Model of Temperature Offset');

%% New Functions

function [table, offset, t_stable, ambient_temp] = extractOffsetWithAmbient(data, name)
% Extracts the offset between mean of liquid of stable phase and target
% temperature, defines the stable point and extracts its temperature and time value,
% calculates the mean and std of the stable phase, and includes ambient temperature
%
% Inputs: data as matrix, name of the measurement
% Outputs: table with mean and std and offsets to target temperature of
%          holder and liquid, offset of liquid in stable phase, time to reach
%          stable phase (t_stable), mean ambient temperature during stable phase

    % Get target temperature (column 4)
    target_temp = data(1, 4);
    
    % Separate time and temperature data
    time = data(:, 1) - data(1, 1); % time in seconds since start
    
    % Temperature data columns
    holder_temp = data(:, 2);
    liquid_temp = data(:, 3);
    ambient_temp_data = data(:, 5); % Room temperature is in column 5
    
    % Find stable region (last 20% of data points)
    stable_idx = round(0.8 * length(time)):length(time);
    
    % Calculate statistics for stable region
    holder_stable_mean = mean(holder_temp(stable_idx));
    holder_stable_std = std(holder_temp(stable_idx));
    liquid_stable_mean = mean(liquid_temp(stable_idx));
    liquid_stable_std = std(liquid_temp(stable_idx));
    ambient_stable_mean = mean(ambient_temp_data(stable_idx));
    ambient_stable_std = std(ambient_temp_data(stable_idx));
    
    % Calculate offsets from target temperature
    holder_offset = holder_stable_mean - target_temp;
    liquid_offset = liquid_stable_mean - target_temp;
    
    % Calculate time to reach stable phase (when liquid is within 0.5°C of stable mean)
    stability_threshold = 0.5;
    stable_reached = false;
    t_stable = NaN;
    
    for i = 1:length(time)
        if abs(liquid_temp(i) - liquid_stable_mean) < stability_threshold
            stable_reached = true;
            t_stable = time(i);
            break;
        end
    end
    
    % If stable point not found, use halfway point
    if ~stable_reached
        t_stable = time(round(length(time)/2));
    end
    
    % Create table of results
    table = struct();
    table.target_temp = target_temp;
    table.holder_mean = holder_stable_mean;
    table.holder_std = holder_stable_std;
    table.holder_offset = holder_offset;
    table.liquid_mean = liquid_stable_mean;
    table.liquid_std = liquid_stable_std;
    table.liquid_offset = liquid_offset;
    table.ambient_mean = ambient_stable_mean;
    table.ambient_std = ambient_stable_std;
    table.t_stable = t_stable;
    
    % Set outputs
    offset = liquid_offset;
    ambient_temp = ambient_stable_mean;
    
    % Display results
    fprintf('\n--- Results for %s ---\n', name);
    fprintf('Target Temperature: %.2f°C\n', target_temp);
    fprintf('Liquid Temperature (stable): %.2f ± %.3f°C (offset: %.2f°C)\n', ...
            liquid_stable_mean, liquid_stable_std, liquid_offset);
    fprintf('Holder Temperature (stable): %.2f ± %.3f°C (offset: %.2f°C)\n', ...
            holder_stable_mean, holder_stable_std, holder_offset);
    fprintf('Ambient Temperature (stable): %.2f ± %.3f°C\n', ...
            ambient_stable_mean, ambient_stable_std);
    fprintf('Time to reach stability: %.1f seconds\n', t_stable);
end

%% Function to implement the updated formula in LabVIEW
function corrected_target = calculateCorrectedTarget(desired_liquid_temp, ambient_temp, coeffs, reference_temp)
% Calculates the corrected target temperature for the holder to achieve the desired
% liquid temperature, taking into account ambient temperature effects
%
% Inputs:
%   desired_liquid_temp - The desired temperature of the liquid
%   ambient_temp - The current ambient temperature
%   coeffs - Model coefficients [a, b, c, d] for y = a*x^2 + b*x + c + d*(T_ambient - T_ref)
%   reference_temp - Reference temperature used in the model
%
% Output:
%   corrected_target - The target temperature to set for the holder

    % Extract coefficients
    a = coeffs(1);
    b = coeffs(2);
    d = coeffs(3);
    c = coeffs(4);
    
    % Account for ambient temperature effect
    ambient_effect = d * (ambient_temp - reference_temp);
    
    % For the quadratic equation: a*x^2 + b*x + (c + ambient_effect - desired_offset) = 0
    % where desired_offset = 0 (we want liquid_temp = desired_liquid_temp)
    
    % Solve quadratic equation
    % We use: ax^2 + bx + e = 0 where e = c + ambient_effect
    e = c + ambient_effect;
    
    % Calculate discriminant
    discriminant = b^2 - 4*a*e;
    
    if discriminant < 0
        % No real solutions
        warning('No solution found. Using linear approximation.');
        corrected_target = desired_liquid_temp - (e/b);
    else
        % Two solutions, usually the smaller one is physically meaningful
        sol1 = (-b + sqrt(discriminant)) / (2*a);
        sol2 = (-b - sqrt(discriminant)) / (2*a);
        
        % Choose the solution that's closer to the desired temperature
        % (usually this is the smaller solution for cooling applications)
        if abs(sol1 - desired_liquid_temp) < abs(sol2 - desired_liquid_temp)
            corrected_target = sol1;
        else
            corrected_target = sol2;
        end
    end
end

%% Implementation Example for LabVIEW Integration
% This shows how to calculate holder target temperatures for various 
% desired liquid temperatures and ambient conditions

fprintf('\n--- Example Calculations for LabVIEW Integration ---\n');
desired_temps = [5, 15, 25, 35, 45];
ambient_temps = [18, 20, 22, 25];

% Use either the fitted coefficients or input your own
model_coeffs = coeffs;  % [a, b, d, c] from the fit above
ref_temp = reference_temp;

% Create a table of results
fprintf('Desired Liquid Temp | Ambient Temp | Holder Target Temp\n');
fprintf('--------------------------------------------------\n');

for i = 1:length(desired_temps)
    for j = 1:length(ambient_temps)
        desired_temp = desired_temps(i);
        ambient_temp = ambient_temps(j);
        
        corrected_target = calculateTarget(desired_temp, ambient_temp, model_coeffs, ref_temp);
        
        fprintf('      %.1f°C      |     %.1f°C    |      %.2f°C\n', ...
                desired_temp, ambient_temp, corrected_target);
    end
    fprintf('--------------------------------------------------\n');
end