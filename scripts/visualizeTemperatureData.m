%% Temperature Visualization Script
% This script visualizes temperature measurement data, showing the target temperature,
% the acceptable range (±0.5°C), and the actual temperature measurements over time.

%% Setup
% Add source directories to path
addpath(genpath('../src/'));

%% File Selection
% Define data directory
dataDir = '../data/raw/';

% Default file if user doesn't specify one
defaultFile = '27.03.25,12.07,20.0_30.0_1.0_5.xlsx';
prompt = sprintf('Enter filename (or press Enter for default: %s): ', defaultFile);
userInput = input(prompt, 's');

if isempty(userInput)
    filename = defaultFile;
else
    filename = userInput;
end

% Full file path
filepath = fullfile(dataDir, filename);

% Verify file exists
if ~exist(filepath, 'file')
    error('File not found: %s', filepath);
end

fprintf('Visualizing data from: %s\n', filename);

% Allow for manual override of target temperature
prompt = 'Override target temperature? (y/n): ';
overrideResponse = input(prompt, 's');
overrideTarget = false;
manualTargetTemp = NaN;

if strcmpi(overrideResponse, 'y')
    prompt = 'Enter the correct target temperature in °C: ';
    manualTargetTemp = input(prompt);
    overrideTarget = true;
    fprintf('Using manual target temperature: %.1f°C\n', manualTargetTemp);
end

%% Read Data
try
    % Read measurement data and settings
    data = readMeasurement(filename, filepath);
    settings = readSettings(filename);
    fprintf('Successfully read data: %d rows, %d columns\n', size(data, 1), size(data, 2));
catch ME
    error('Error reading data: %s', ME.message);
end

%% Process Data
% Check if data contains temperature steps
hasSteps = settings.increment ~= 0 && settings.startTemp ~= settings.stopTemp;

if hasSteps
    try
        % Split data into temperature steps
        steps = splitTempSteps(data, settings);
        fprintf('Found %d temperature steps\n', length(steps));
        
        % Let user choose step to visualize
        prompt = sprintf('Enter step number (1-%d) or press Enter for all: ', length(steps));
        choice = input(prompt, 's');
        
        if isempty(choice)
            % Visualize all steps
            for i = 1:length(steps)
                % Apply manual target override if specified
                if overrideTarget
                    actualTargetTemp = manualTargetTemp;
                else
                    actualTargetTemp = settings.startTemp + (i-1) * settings.increment;
                end
                visualizeTemperature(steps{i}, sprintf('Step %d (Target Liquid: %.1f°C)', i, actualTargetTemp), actualTargetTemp);
            end
        else
            % Visualize specific step
            stepNum = str2double(choice);
            if isnan(stepNum) || stepNum < 1 || stepNum > length(steps)
                error('Invalid step number: %s', choice);
            end
            % Apply manual target override if specified
            if overrideTarget
                actualTargetTemp = manualTargetTemp;
            else
                actualTargetTemp = settings.startTemp + (stepNum-1) * settings.increment;
            end
            visualizeTemperature(steps{stepNum}, sprintf('Step %d (Target Liquid: %.1f°C)', stepNum, actualTargetTemp), actualTargetTemp);
        end
    catch ME
        warning('Error splitting steps: %s\nTreating as single measurement.', ME.message);
        % For single measurements, apply manual target override if specified
        if overrideTarget
            actualTargetTemp = manualTargetTemp;
        else
            actualTargetTemp = settings.startTemp;
        end
        visualizeTemperature(data, 'Temperature Measurement', actualTargetTemp);
    end
else
    % Visualize single measurement
    % Apply manual target override if specified
    if overrideTarget
        actualTargetTemp = manualTargetTemp;
    else
        actualTargetTemp = settings.startTemp;
    end
    visualizeTemperature(data, 'Temperature Measurement', actualTargetTemp);
end

%% Visualization Function
function visualizeTemperature(data, titleText, targetLiquidTemp)
    % Extract data
    timeSeconds = data(:, 1) - data(1, 1);
    timeHours = timeSeconds / 3600;
    holderTemp = data(:, 2);
    liquidTemp = data(:, 3);
    holderTargetTemp = mean(data(:, 4));
    
    % Use the provided target liquid temperature for comparison
    targetTemp = targetLiquidTemp;
    
    % Define acceptable range (±0.5°C)
    upperBound = targetTemp + 0.5;
    lowerBound = targetTemp - 0.5;
    
    % Create figure
    figure('Name', 'Temperature Visualization', 'Position', [100 100 900 500]);
    hold on;
    
    % Plot target temperature range
    fill([timeHours(1); timeHours(end); timeHours(end); timeHours(1)], ...
         [lowerBound; lowerBound; upperBound; upperBound], ...
         [0.9 0.9 1], 'EdgeColor', 'none', 'DisplayName', 'Target Range (±0.5°C)');
    
    % Plot target temperature line
    line([timeHours(1), timeHours(end)], [targetTemp, targetTemp], ...
         'Color', 'b', 'LineStyle', '--', 'LineWidth', 1.5, 'DisplayName', 'Target Temperature');
    
    % Plot actual temperatures
    plot(timeHours, holderTemp, 'r-', 'LineWidth', 1, 'DisplayName', 'Holder Temperature');
    plot(timeHours, liquidTemp, 'g-', 'LineWidth', 1.5, 'DisplayName', 'Liquid Temperature');
    
    % Add labels and formatting
    xlabel('Time (hours)');
    ylabel('Temperature (°C)');
    title(titleText);
    legend('Location', 'best');
    grid on;
    
    % Calculate statistics for stable region (last 20% of data)
    stableIdx = round(0.8 * length(timeHours)):length(timeHours);
    liquidStableMean = mean(liquidTemp(stableIdx));
    liquidStableStd = std(liquidTemp(stableIdx));
    holderStableMean = mean(holderTemp(stableIdx));
    holderStableStd = std(holderTemp(stableIdx));
    
    % Display statistics
    fprintf('\n--- Stable Region Statistics ---\n');
    fprintf('Target Liquid Temperature: %.2f°C (Range: %.2f to %.2f°C)\n', targetTemp, lowerBound, upperBound);
    fprintf('Actual Liquid Temperature: %.2f ± %.3f°C\n', liquidStableMean, liquidStableStd);
    fprintf('Holder Temperature: %.2f ± %.3f°C (target: %.2f°C)\n', holderStableMean, holderStableStd, holderTargetTemp);
    
    % Check if temperature is within specification
    withinSpec = (liquidStableMean >= lowerBound && liquidStableMean <= upperBound && liquidStableStd <= 0.25);
    
    if withinSpec
        fprintf('✓ Temperature maintained within specifications\n');
    else
        fprintf('✗ Temperature outside specifications\n');
        if liquidStableMean < lowerBound || liquidStableMean > upperBound
            fprintf('  Mean outside range: %.2f°C (should be between %.2f and %.2f°C)\n', ...
                    liquidStableMean, lowerBound, upperBound);
        end
        if liquidStableStd > 0.25
            fprintf('  Standard deviation too high: %.3f°C (should be ≤ 0.25°C)\n', liquidStableStd);
        end
    end
    
    % Add annotation to the plot with statistics
    textPos = [0.02, 0.15]; % normalized position
    str = sprintf(['Statistics (stable region):\n', ...
                   'Target Liquid: %.2f°C (±0.5°C)\n', ...
                   'Actual Liquid: %.2f ± %.3f°C\n', ...
                   'Holder: %.2f ± %.3f°C\n', ...
                   'Holder Target: %.2f°C'], ...
                   targetTemp, liquidStableMean, liquidStableStd, ...
                   holderStableMean, holderStableStd, holderTargetTemp);
    
    annotation('textbox', [textPos, 0.3, 0.1], 'String', str, 'FitBoxToText', 'on', ...
               'BackgroundColor', [1 1 1], 'EdgeColor', [0.7 0.7 0.7]);
end