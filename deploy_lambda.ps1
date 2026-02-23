# Lambda Packaging Script for AML Web Search
# This script creates a zip file for deployment to AWS Lambda.

$projectName = "aml_web_search"
$zipFile = "lambda_function.zip"
$filesToInclude = @("aws_lambda_search.py")

Write-Host "--- Packaging Lambda Function ---" -ForegroundColor Cyan

if (Test-Path $zipFile) {
    Remove-Item $zipFile -Force
    Write-Host "Removed existing $zipFile" -ForegroundColor Yellow
}

# Ensure the file is at the root of the archive
Compress-Archive -Path $filesToInclude -DestinationPath $zipFile -Force

if (Test-Path $zipFile) {
    Write-Host "SUCCESS: Created $zipFile at $(Get-Location)" -ForegroundColor Green
    Write-Host "Next Steps:"
    Write-Host "1. Upload $zipFile to the AWS Lambda Console."
    Write-Host "2. Set the Handler to: aws_lambda_search.lambda_handler"
} else {
    Write-Host "ERROR: Failed to create $zipFile" -ForegroundColor Red
}
