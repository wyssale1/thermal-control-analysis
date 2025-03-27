function [table, offset, t_stable, ambient_temp] = extractOffsetWithAmbient(data, name)
%----------------------------------------------------------------
% Extracts offset information including ambient temperature
% Inputs: data matrix, step name
% Outputs: table of results, liquid offset, time to stability, ambient temp
%----------------------------------------------------------------
    % Get temperatures from data
    target_temp = mean(data(:, 4));  % Target temperature (use mean)
    holder_temp = data(:, 2);        % Holder temperature
    liquid_temp = data(:, 3);        % Liquid temperature
    ambient_temp_data = data(:, 5);  % Room temperature
    time = data(:, 1) - data(1, 1);  % Relative time
    
    % Find stable period (last 20% of data)
    stable_idx = round(0.8 * length(time)):length(time);
    
    % Calculate statistics for stable period
    holder_stable_mean = mean(holder_temp(stable_idx));
    holder_stable_std = std(holder_temp(stable_idx));
    liquid_stable_mean = mean(liquid_temp(stable_idx));
    liquid_stable_std = std(liquid_temp(stable_idx));
    ambient_stable_mean = mean(ambient_temp_data(stable_idx));
    ambient_stable_std = std(ambient_temp_data(stable_idx));
    
    % Calculate offsets
    holder_offset = holder_stable_mean - target_temp;
    liquid_offset = liquid_stable_mean - target_temp;
    
    % Determine time to stability
    stability_threshold = 0.5;
    t_stable = NaN;
    
    for i = 1:length(time)
        if abs(liquid_temp(i) - liquid_stable_mean) < stability_threshold
            t_stable = time(i);
            break;
        end
    end
    
    if isnan(t_stable)
        t_stable = time(end)/2;  % Default to half of total time if not found
    end
    
    % Create results table
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
    
    % Set output variables
    offset = liquid_offset;
    ambient_temp = ambient_stable_mean;
    
    % Print results
    fprintf('Results for %s:\n', name);
    fprintf('  Target Temperature: %.2f°C\n', target_temp);
    fprintf('  Holder Temperature: %.2f ± %.3f°C (offset: %.2f°C)\n', ...
            holder_stable_mean, holder_stable_std, holder_offset);
    fprintf('  Liquid Temperature: %.2f ± %.3f°C (offset: %.2f°C)\n', ...
            liquid_stable_mean, liquid_stable_std, liquid_offset);
    fprintf('  Ambient Temperature: %.2f ± %.3f°C\n', ...
            ambient_stable_mean, ambient_stable_std);
    fprintf('  Time to stability: %.1f seconds\n', t_stable);
end