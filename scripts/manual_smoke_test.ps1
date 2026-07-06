param(
    [string]$BaseUrl = "http://127.0.0.1:5000"
)

$ErrorActionPreference = "Stop"

$AdminEmail = "admin@example.com"
$AdminPassword = "Admin12345"
$TempPassword = "TempUser12345"
$RunId = "{0}-{1}" -f (Get-Date -Format "yyyyMMddHHmmss"), ([guid]::NewGuid().ToString("N").Substring(0, 8))
$TempEmail = "smoke-$RunId@example.com"

function Redact-Body {
    param([string]$Body)

    if ([string]::IsNullOrWhiteSpace($Body)) {
        return "<empty>"
    }

    $redacted = $Body
    $redacted = $redacted -replace '("token"\s*:\s*")[^"]+(")', '$1<redacted>$2'
    $redacted = $redacted -replace '("password"\s*:\s*")[^"]+(")', '$1<redacted>$2'
    $redacted = $redacted -replace '("password_repeat"\s*:\s*")[^"]+(")', '$1<redacted>$2'
    $redacted = $redacted -replace '("password_hash"\s*:\s*")[^"]+(")', '$1<redacted>$2'

    if ($redacted.Length -gt 300) {
        return $redacted.Substring(0, 300) + "...<truncated>"
    }

    return $redacted
}

function ConvertTo-ShortJson {
    param($Value)
    return ($Value | ConvertTo-Json -Depth 12 -Compress)
}

function Invoke-Api {
    param(
        [Parameter(Mandatory = $true)][string]$Method,
        [Parameter(Mandatory = $true)][string]$Path,
        $Body = $null,
        [string]$Token = $null
    )

    $headers = @{}
    if ($Token) {
        $headers["Authorization"] = "Bearer $Token"
    }

    $uri = "$BaseUrl$Path"
    $parameters = @{
        Method      = $Method
        Uri         = $uri
        Headers     = $headers
        ContentType = "application/json"
    }
    if ((Get-Command Invoke-WebRequest).Parameters.ContainsKey("SkipHttpErrorCheck")) {
        $parameters["SkipHttpErrorCheck"] = $true
    }

    if ($null -ne $Body) {
        $parameters["Body"] = ConvertTo-ShortJson $Body
    }

    try {
        $response = Invoke-WebRequest @parameters
        $content = [string]$response.Content
        $json = $null
        if (-not [string]::IsNullOrWhiteSpace($content)) {
            try {
                $json = $content | ConvertFrom-Json
            }
            catch {
                $json = $null
            }
        }

        return [pscustomobject]@{
            StatusCode = [int]$response.StatusCode
            Body       = $content
            Json       = $json
        }
    }
    catch {
        $statusCode = 0
        $content = $_.Exception.Message

        if ($_.Exception.Response) {
            $statusCode = [int]$_.Exception.Response.StatusCode
            try {
                if ($_.Exception.Response.Content) {
                    $content = $_.Exception.Response.Content.ReadAsStringAsync().GetAwaiter().GetResult()
                }
                elseif ($_.Exception.Response.GetResponseStream) {
                    $stream = $_.Exception.Response.GetResponseStream()
                    $reader = [System.IO.StreamReader]::new($stream)
                    $content = $reader.ReadToEnd()
                    $reader.Dispose()
                }
            }
            catch {
                $content = $_.Exception.Message
            }
        }

        $json = $null
        if (-not [string]::IsNullOrWhiteSpace($content)) {
            try {
                $json = $content | ConvertFrom-Json
            }
            catch {
                $json = $null
            }
        }

        return [pscustomobject]@{
            StatusCode = $statusCode
            Body       = $content
            Json       = $json
        }
    }
}

function Write-Result {
    param(
        [Parameter(Mandatory = $true)][string]$State,
        [Parameter(Mandatory = $true)][string]$Name,
        [Parameter(Mandatory = $true)]$Response,
        [string]$Details = ""
    )

    $line = "$State - $Name - status $($Response.StatusCode) - body: $(Redact-Body $Response.Body)"
    if ($Details) {
        $line = "$line - $Details"
    }
    Write-Host $line
}

function Assert-Check {
    param(
        [Parameter(Mandatory = $true)][string]$Name,
        [Parameter(Mandatory = $true)]$Response,
        [Parameter(Mandatory = $true)][scriptblock]$Condition,
        [string]$Details = ""
    )

    if (& $Condition) {
        Write-Result "PASS" $Name $Response $Details
        return
    }

    Write-Result "FAIL" $Name $Response $Details
    exit 1
}

function Require-JsonField {
    param(
        [Parameter(Mandatory = $true)]$Json,
        [Parameter(Mandatory = $true)][string]$FieldName,
        [Parameter(Mandatory = $true)][string]$CheckName,
        [Parameter(Mandatory = $true)]$Response
    )

    if ($null -eq $Json -or -not ($Json.PSObject.Properties.Name -contains $FieldName) -or [string]::IsNullOrWhiteSpace([string]$Json.$FieldName)) {
        Write-Result "FAIL" $CheckName $Response "missing JSON field '$FieldName'"
        exit 1
    }

    return $Json.$FieldName
}

Write-Host "Manual smoke test target: $BaseUrl"
Write-Host "Temporary user email: $TempEmail"

$health = Invoke-Api -Method "GET" -Path "/api/health"
Assert-Check "1. Health endpoint returns 200" $health { $health.StatusCode -eq 200 }

$registerBody = @{
    email           = $TempEmail
    password        = $TempPassword
    password_repeat = $TempPassword
    first_name      = "Smoke"
    last_name       = "Tester"
    middle_name     = "Manual"
}
$register = Invoke-Api -Method "POST" -Path "/api/auth/register" -Body $registerBody
Assert-Check "2. Register a unique temporary user" $register {
    $register.StatusCode -eq 201 -and
    $register.Json.user.email -eq $TempEmail -and
    $null -ne $register.Json.user.id
}
$TempUserId = [int]$register.Json.user.id

$login = Invoke-Api -Method "POST" -Path "/api/auth/login" -Body @{
    email    = $TempEmail
    password = $TempPassword
}
$TempToken = Require-JsonField $login.Json "token" "3. Login returns a bearer token" $login
Assert-Check "3. Login returns a bearer token" $login {
    $login.StatusCode -eq 200 -and
    $login.Json.token_type -eq "Bearer" -and
    -not [string]::IsNullOrWhiteSpace($TempToken)
}

$me = Invoke-Api -Method "GET" -Path "/api/auth/me" -Token $TempToken
Assert-Check "4. GET current user works with the token" $me {
    $me.StatusCode -eq 200 -and
    $me.Json.user.email -eq $TempEmail
}

$projectsNoToken = Invoke-Api -Method "POST" -Path "/api/projects"
Assert-Check "5. Protected business endpoint without a token returns 401" $projectsNoToken {
    $projectsNoToken.StatusCode -eq 401
}

$projectsForbidden = Invoke-Api -Method "POST" -Path "/api/projects" -Token $TempToken
Assert-Check "6. Authenticated user without permission receives 403" $projectsForbidden {
    $projectsForbidden.StatusCode -eq 403
}

$adminLogin = Invoke-Api -Method "POST" -Path "/api/auth/login" -Body @{
    email    = $AdminEmail
    password = $AdminPassword
}
$AdminToken = Require-JsonField $adminLogin.Json "token" "7. Login as the existing seeded administrator" $adminLogin
Assert-Check "7. Login as the existing seeded administrator" $adminLogin {
    $adminLogin.StatusCode -eq 200 -and
    $adminLogin.Json.token_type -eq "Bearer" -and
    -not [string]::IsNullOrWhiteSpace($AdminToken)
}

$rules = Invoke-Api -Method "GET" -Path "/api/admin/rules" -Token $AdminToken
Assert-Check "8. Load admin rules before assigning access" $rules {
    $rules.StatusCode -eq 200 -and
    $null -ne $rules.Json.roles
}

$managerRole = $rules.Json.roles | Where-Object { $_.code -eq "manager" } | Select-Object -First 1
if ($null -eq $managerRole) {
    Write-Result "FAIL" "8. Through the admin API, assign the required role or permission to the temporary user" $rules "seeded manager role was not found"
    exit 1
}

$assignRole = Invoke-Api -Method "POST" -Path "/api/admin/user-roles" -Token $AdminToken -Body @{
    user_id = $TempUserId
    role_id = [int]$managerRole.id
}
Assert-Check "8. Through the admin API, assign the required role or permission to the temporary user" $assignRole {
    $assignRole.StatusCode -eq 201 -and
    $assignRole.Json.user_role.user_id -eq $TempUserId -and
    $assignRole.Json.user_role.role.code -eq "manager"
}
$AssignedUserRoleId = [int]$assignRole.Json.user_role.id

$projectsAllowed = Invoke-Api -Method "POST" -Path "/api/projects" -Token $TempToken
Assert-Check "9. The temporary user can now access the previously forbidden business operation successfully" $projectsAllowed {
    $projectsAllowed.StatusCode -eq 201
}

$removeRole = Invoke-Api -Method "DELETE" -Path "/api/admin/user-roles/$AssignedUserRoleId" -Token $AdminToken
Assert-Check "10. Remove that role or permission through the admin API" $removeRole {
    $removeRole.StatusCode -eq 200
}

$projectsForbiddenAgain = Invoke-Api -Method "POST" -Path "/api/projects" -Token $TempToken
Assert-Check "11. The same operation returns 403 again" $projectsForbiddenAgain {
    $projectsForbiddenAgain.StatusCode -eq 403
}

$logout = Invoke-Api -Method "POST" -Path "/api/auth/logout" -Token $TempToken
Assert-Check "12. Logout revokes the bearer token" $logout {
    $logout.StatusCode -eq 200
}

$reuseRevoked = Invoke-Api -Method "GET" -Path "/api/auth/me" -Token $TempToken
Assert-Check "13. Reusing the revoked token returns 401" $reuseRevoked {
    $reuseRevoked.StatusCode -eq 401
}

$secondLogin = Invoke-Api -Method "POST" -Path "/api/auth/login" -Body @{
    email    = $TempEmail
    password = $TempPassword
}
$SecondTempToken = Require-JsonField $secondLogin.Json "token" "14. Login again before soft-delete" $secondLogin
Assert-Check "14. Login again before soft-delete" $secondLogin {
    $secondLogin.StatusCode -eq 200 -and
    -not [string]::IsNullOrWhiteSpace($SecondTempToken)
}

$softDelete = Invoke-Api -Method "DELETE" -Path "/api/auth/me" -Token $SecondTempToken
Assert-Check "14. Soft-delete the temporary account" $softDelete {
    $softDelete.StatusCode -eq 200
}

$usersAfterDelete = Invoke-Api -Method "GET" -Path "/api/admin/users" -Token $AdminToken
$deletedUser = $usersAfterDelete.Json.items | Where-Object { $_.email -eq $TempEmail } | Select-Object -First 1
Assert-Check "14. Verify the account becomes inactive and the database record still exists" $usersAfterDelete {
    $usersAfterDelete.StatusCode -eq 200 -and
    $null -ne $deletedUser -and
    $deletedUser.is_active -eq $false
}

$loginAfterDelete = Invoke-Api -Method "POST" -Path "/api/auth/login" -Body @{
    email    = $TempEmail
    password = $TempPassword
}
Assert-Check "14. Verify login is rejected after soft-delete" $loginAfterDelete {
    $loginAfterDelete.StatusCode -eq 401
}

Write-Host "PASS - All manual smoke checks passed"
exit 0
