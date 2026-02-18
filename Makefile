UUID = cintile@forgetting.me
EXT_DIR = $(HOME)/.local/share/cinnamon/extensions/$(UUID)
SRC_FILES = extension.js common.js metadata.json settings-schema.json

.PHONY: deploy restart logs clean

deploy:
	@mkdir -p $(EXT_DIR)
	@cp -v $(SRC_FILES) $(EXT_DIR)/
	@echo "✓ Deployed to $(EXT_DIR)"

restart:
	@echo "Restarting Cinnamon..."
	@nohup cinnamon --replace &>/dev/null &
	@echo "✓ Cinnamon restarting"

deploy-restart: deploy restart

logs:
	@journalctl /usr/bin/cinnamon -f --no-pager | grep -i cintile

clean:
	@rm -rf $(EXT_DIR)
	@echo "✓ Removed $(EXT_DIR)"
