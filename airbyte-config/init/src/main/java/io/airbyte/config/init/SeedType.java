package io.airbyte.config.init;

public enum SeedType {

  STANDARD_SOURCE_DEFINITION("/seed/source_definitions.yaml", "sourceDefinitionId"),
  STANDARD_DESTINATION_DEFINITION("/seed/destination_definitions.yaml", "destinationDefinitionId");

  final String resourcePath;
  // ID field name
  final String idName;

  SeedType(String resourcePath, String idName) {
    this.resourcePath = resourcePath;
    this.idName = idName;
  }

  public String getResourcePath() {
    return resourcePath;
  }

  public String getIdName() {
    return idName;
  }

}
