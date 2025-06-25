FROM mcr.microsoft.com/dotnet/sdk:8.0 AS build
WORKDIR /app
RUN dotnet new web -n AffiApi
WORKDIR /app/AffiApi
COPY *.cs ./
RUN dotnet add package Google.Cloud.Firestore \
&& dotnet publish -c Release -o /out

FROM mcr.microsoft.com/dotnet/aspnet:8.0
WORKDIR /app
COPY --from=build /out ./
RUN adduser -u 5678 --disabled-password --gecos "" appuser \
&& chown -R appuser .
USER appuser
EXPOSE 8080
ENTRYPOINT ["dotnet", "AffiApi.dll"]