function corrected_target = calculateCorrectedTarget(desired_liquid_temp, ambient_temp, coeffs, reference_temp)
%----------------------------------------------------------------
% Calculates required holder temperature to achieve desired liquid temperature
% Inputs: desired_liquid_temp, ambient_temp, model coeffs, reference_temp
% Output: corrected_target holder temperature
%----------------------------------------------------------------
    % Extract coefficients
    a = coeffs(1);  % x^2 coefficient
    b = coeffs(2);  % x coefficient
    c = coeffs(3);  % ambient temp coefficient
    d = coeffs(4);  % constant term
    
    % Calculate ambient temperature effect
    ambient_effect = c * (ambient_temp - reference_temp);
    
    % Solve quadratic equation: a*x^2 + b*x + (d + ambient_effect - desired_liquid_temp) = 0
    e = d + ambient_effect;
    
    % Desired offset is 0 (liquid_temp = target_temp + offset)
    discriminant = b^2 - 4*a*(e);
    
    if discriminant < 0
        % No real solution - use linear approximation
        corrected_target = desired_liquid_temp - e/b;
        warning('No exact solution found. Using linear approximation for %.1f°C.', desired_liquid_temp);
    else
        % Find both solutions
        sol1 = (-b + sqrt(discriminant)) / (2*a);
        sol2 = (-b - sqrt(discriminant)) / (2*a);
        
        % Choose the solution closest to the desired temperature
        % (usually the smaller one for cooling, larger one for heating)
        if abs(sol1 - desired_liquid_temp) < abs(sol2 - desired_liquid_temp)
            corrected_target = sol1;
        else
            corrected_target = sol2;
        end
    end
end