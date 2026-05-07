# Multi-stage Dockerfile for the SOM Skill Worker + Dashboard
# Targets .NET 10. Update tags from "10.0-preview" to "10.0" once .NET 10 reaches GA.

FROM mcr.microsoft.com/dotnet/sdk:10.0-preview AS build
WORKDIR /src
COPY *.csproj ./
RUN dotnet restore
COPY . .
RUN dotnet publish -c Release -o /app

FROM mcr.microsoft.com/dotnet/aspnet:10.0-preview
WORKDIR /app
COPY --from=build /app .
COPY seed-stories/ seed-stories/
COPY skills/ skills/
ENV ASPNETCORE_URLS=http://+:8080
EXPOSE 8080
ENTRYPOINT ["dotnet", "SomSkillWorker.dll"]
