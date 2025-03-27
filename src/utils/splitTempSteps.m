function steps = splitTempSteps(data, properties)
%----------------------------------------------------------------
% This function splits the data into temperature steps
% Inputs: data matrix, properties struct
% Output: cell array of data snippets per temperature step
%----------------------------------------------------------------
    % Initialize steps array
    steps = {};
    
    % Calculate expected number of steps
    if properties.increment == 0
        % Single temperature measurement
        steps{1} = data;
        return;
    end
    
    % Define increment (ensure it's not zero)
    increment = properties.increment;
    if increment == 0
        increment = 1;
        warning('Increment is zero. Using 1°C as default.');
    end
    
    % Calculate number of steps
    expected_steps = floor(abs((properties.stopTemp - properties.startTemp) / increment)) + 1;
    
    % Get target temperature column
    target_temps = data(:, 4);
    
    % Try to find temperature changes
    temp_changes = find(abs(diff(target_temps)) > 0.1);
    
    if length(temp_changes) >= expected_steps - 1
        % We found enough temperature change points
        fprintf('Detected %d temperature changes in the data.\n', length(temp_changes));
        
        % Add start and end points
        step_points = [1; temp_changes + 1; length(target_temps) + 1];
        
        % Create steps from these points
        for i = 1:length(step_points) - 1
            step_data = data(step_points(i):step_points(i+1)-1, :);
            if ~isempty(step_data)
                steps{end+1} = step_data;
            end
        end
    else
        % Fallback: Split by equal time segments
        fprintf('Could not detect enough temperature changes. Splitting data into %d equal parts.\n', expected_steps);
        segment_size = floor(size(data, 1) / expected_steps);
        
        for i = 1:expected_steps
            start_idx = (i-1) * segment_size + 1;
            if i == expected_steps
                end_idx = size(data, 1);  % Last segment gets any remaining points
            else
                end_idx = i * segment_size;
            end
            steps{i} = data(start_idx:end_idx, :);
        end
    end
    
    % Validate we have data in each step
    for i = length(steps):-1:1
        if size(steps{i}, 1) < 10  % Require at least 10 data points
            warning('Step %d has only %d points. Removing it.', i, size(steps{i}, 1));
            steps(i) = [];
        end
    end
    
    fprintf('Created %d temperature steps.\n', length(steps));
    
    % Print info about each step
    for i = 1:length(steps)
        avg_target = mean(steps{i}(:, 4));
        fprintf('  Step %d: Average target temp = %.2f°C, %d data points\n', ...
                i, avg_target, size(steps{i}, 1));
    end
end