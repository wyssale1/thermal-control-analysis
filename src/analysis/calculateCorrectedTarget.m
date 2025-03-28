function corrected_target = calculateCorrectedTarget(desired_liquid_temp, ambient_temp, coeffs, reference_temp)
%----------------------------------------------------------------
% Calculates required holder temperature to achieve desired liquid temperature
% Inputs: desired_liquid_temp, ambient_temp, model coeffs, reference_temp
%         coeffs = [a, b, c, d] from model: 
%         offset = a*target^2 + b*target + c*(ambient - ref) + d
%         where offset = liquid_temp - target_temp
% Output: corrected_target holder temperature (x)
%----------------------------------------------------------------
    % Extract coefficients (ensure order matches analyzeTemperature.m fit)
    a = coeffs(1);  % x^2 coefficient
    b = coeffs(2);  % x coefficient
    c = coeffs(3);  % ambient temp coefficient
    d = coeffs(4);  % constant term

    % Calculate ambient temperature effect component
    ambient_effect_term = c * (ambient_temp - reference_temp);

    % We want liquid_temp = desired_liquid_temp
    % Since offset = liquid_temp - target_temp, we substitute:
    % offset = desired_liquid_temp - target_temp
    %
    % desired_liquid_temp - target = a*target^2 + b*target + ambient_effect_term + d
    % Rearranging to solve for target (let target = x):
    % a*x^2 + b*x + x + d + ambient_effect_term - desired_liquid_temp = 0
    % a*x^2 + (b+1)*x + (d + ambient_effect_term - desired_liquid_temp) = 0

    % Coefficients for the standard quadratic equation format Ax^2 + Bx + C = 0
    A_quad = a;
    B_quad = b + 1; 
    C_quad = d + ambient_effect_term - desired_liquid_temp;

    % Calculate discriminant
    discriminant = B_quad^2 - 4*A_quad*C_quad;

    if discriminant < 0
        % No real solution - may indicate model issues or desired temp out of range
        % Using a linear approximation as fallback (solving Bx + C = 0)
        corrected_target = -C_quad / B_quad; 
        warning('Quadratic solver: No real solution found for desired_liquid_temp=%.2f, ambient=%.2f. Using linear approximation based on Bx+C=0, resulting target=%.2f.', desired_liquid_temp, ambient_temp, corrected_target);
        if isnan(corrected_target) || isinf(corrected_target)
            % If linear approx also fails (e.g., B_quad is zero)
            corrected_target = desired_liquid_temp; % Failsafe: set target = desired
             warning('Quadratic solver: Linear approximation failed. Using failsafe target = desired_liquid_temp.');
        end
    else
        % Find both real solutions
        sol1 = (-B_quad + sqrt(discriminant)) / (2*A_quad);
        sol2 = (-B_quad - sqrt(discriminant)) / (2*A_quad);

        % Choose the appropriate solution. Often, one solution is physically 
        % unrealistic (e.g., extremely high/low). A simple heuristic is
        % to choose the one closer to the desired liquid temperature, but
        % physical understanding of the system might suggest a better rule.
        if abs(sol1 - desired_liquid_temp) <= abs(sol2 - desired_liquid_temp)
            corrected_target = sol1;
        else
            corrected_target = sol2;
        end
        % Optional: Add checks here if corrected_target is outside a reasonable range
        % e.g., if corrected_target < -50 || corrected_target > 150
        %    warning('Quadratic solver: Solution %.2f seems physically unrealistic.', corrected_target);
        % end
    end
end